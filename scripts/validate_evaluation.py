#!/usr/bin/env python3
"""No AI Slop JAの単発パイロット評価ファイルを検証し、判定数を集計する。"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CASES = ROOT / "tests" / "cases.json"
RAW_KIND = "no-ai-slop-ja-raw-output"
JUDGED_KIND = "no-ai-slop-ja-judged-results"
SCHEMA_VERSION = 1
PROMPT_CONSTRUCTION = "skill-md-verbatim-plus-case-json"
STATUSES = {"pass", "fail", "not-applicable"}
CHECK_NAMES = (
    "actor",
    "action",
    "tenseAspect",
    "modality",
    "certainty",
    "causalRelation",
    "numbers",
    "quotes",
    "sources",
    "patternHandling",
    "overEditing",
    "outputFormat",
)
COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


class ValidationError(ValueError):
    """入力ファイルが評価スキーマを満たさない。"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "生のモデル出力JSONと独立判定JSONを検証し、判定に基づく集計をJSONで出力します。"
            "このスクリプトはモデルを実行せず、結果を生成・補完しません。"
        )
    )
    parser.add_argument("--raw", required=True, type=Path, help="生のモデル出力JSON")
    parser.add_argument("--judged", required=True, type=Path, help="独立判定結果JSON")
    parser.add_argument(
        "--cases",
        type=Path,
        default=DEFAULT_CASES,
        help="ケース定義JSON（既定: tests/cases.json）",
    )
    parser.add_argument(
        "--expected-source-commit",
        help="記録されたsourceCommitと一致させる40桁のGitコミットSHA",
    )
    parser.add_argument(
        "--require-all-cases",
        action="store_true",
        help="cases.jsonの全ケースが生出力に含まれることを要求する",
    )
    return parser.parse_args()


def load_json(path: Path, label: str) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise ValidationError(f"{label}を読み込めません: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise ValidationError(f"{label}は有効なJSONではありません: {exc}") from exc
    if not isinstance(data, dict):
        raise ValidationError(f"{label}のルートはオブジェクトでなければなりません")
    return data


def require_exact_keys(value: dict[str, Any], expected: set[str], label: str) -> None:
    actual = set(value)
    if actual != expected:
        missing = sorted(expected - actual)
        extra = sorted(actual - expected)
        raise ValidationError(f"{label}のキーが一致しません: missing={missing}, extra={extra}")


def require_nonempty_string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValidationError(f"{label}は空でない文字列でなければなりません")
    return value


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def resolve_repo_file(relative: str, label: str) -> Path:
    candidate = Path(relative)
    if candidate.is_absolute():
        raise ValidationError(f"{label}はリポジトリ相対パスでなければなりません")
    resolved = (ROOT / candidate).resolve()
    try:
        resolved.relative_to(ROOT.resolve())
    except ValueError as exc:
        raise ValidationError(f"{label}はリポジトリ外を参照できません") from exc
    if not resolved.is_file():
        raise ValidationError(f"{label}のファイルがありません: {relative}")
    return resolved


def validate_identity(value: Any, label: str) -> None:
    if not isinstance(value, dict):
        raise ValidationError(f"{label}はオブジェクトでなければなりません")
    require_exact_keys(value, {"identity", "model"}, label)
    require_nonempty_string(value["identity"], f"{label}.identity")
    require_nonempty_string(value["model"], f"{label}.model")


def validate_source(source: Any, cases_data: dict[str, Any], label: str) -> str:
    if not isinstance(source, dict):
        raise ValidationError(f"{label}はオブジェクトでなければなりません")
    require_exact_keys(
        source,
        {
            "sourceCommit",
            "skillPath",
            "skillSha256",
            "casesPath",
            "casesSha256",
            "casesSchemaVersion",
        },
        label,
    )
    commit = require_nonempty_string(source["sourceCommit"], f"{label}.sourceCommit")
    if not COMMIT_RE.fullmatch(commit):
        raise ValidationError(f"{label}.sourceCommitは40桁の小文字16進Git SHAでなければなりません")

    skill_path_text = require_nonempty_string(source["skillPath"], f"{label}.skillPath")
    cases_path_text = require_nonempty_string(source["casesPath"], f"{label}.casesPath")
    skill_path = resolve_repo_file(skill_path_text, f"{label}.skillPath")
    cases_path = resolve_repo_file(cases_path_text, f"{label}.casesPath")

    for field, path in (("skillSha256", skill_path), ("casesSha256", cases_path)):
        recorded = require_nonempty_string(source[field], f"{label}.{field}")
        if not SHA256_RE.fullmatch(recorded):
            raise ValidationError(f"{label}.{field}は64桁の小文字16進SHA-256でなければなりません")
        actual = file_sha256(path)
        if recorded != actual:
            raise ValidationError(f"{label}.{field}が現在の{path.relative_to(ROOT)}と一致しません")

    if source["casesSchemaVersion"] != cases_data.get("schemaVersion"):
        raise ValidationError(f"{label}.casesSchemaVersionがケース定義と一致しません")
    if cases_path.resolve() != Path(cases_data["_path"]).resolve():
        raise ValidationError(f"{label}.casesPathが--casesと一致しません")
    return commit


def validate_commit_exists(commit: str) -> None:
    result = subprocess.run(
        ["git", "cat-file", "-e", f"{commit}^{{commit}}"],
        cwd=ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    if result.returncode != 0:
        raise ValidationError(f"sourceCommitがこのリポジトリに存在しません: {commit}")


def validate_raw(
    data: dict[str, Any], cases_data: dict[str, Any], known_case_ids: set[str]
) -> tuple[str, list[str]]:
    require_exact_keys(
        data,
        {"schemaVersion", "kind", "source", "runner", "promptConstruction", "outputs"},
        "raw",
    )
    if data["schemaVersion"] != SCHEMA_VERSION or data["kind"] != RAW_KIND:
        raise ValidationError("rawのschemaVersionまたはkindが対応スキーマと一致しません")
    source_commit = validate_source(data["source"], cases_data, "raw.source")
    validate_identity(data["runner"], "raw.runner")
    if data["promptConstruction"] != PROMPT_CONSTRUCTION:
        raise ValidationError(
            f"raw.promptConstructionは{PROMPT_CONSTRUCTION!r}でなければなりません"
        )
    if not isinstance(data["outputs"], list) or not data["outputs"]:
        raise ValidationError("raw.outputsは1件以上の配列でなければなりません")

    ids: list[str] = []
    for index, output in enumerate(data["outputs"]):
        label = f"raw.outputs[{index}]"
        if not isinstance(output, dict):
            raise ValidationError(f"{label}はオブジェクトでなければなりません")
        require_exact_keys(output, {"caseId", "output"}, label)
        case_id = require_nonempty_string(output["caseId"], f"{label}.caseId")
        require_nonempty_string(output["output"], f"{label}.output")
        if case_id not in known_case_ids:
            raise ValidationError(f"未知のcaseIdです: {case_id}")
        if case_id in ids:
            raise ValidationError(f"raw.outputsのcaseIdが重複しています: {case_id}")
        ids.append(case_id)
    return source_commit, ids


def validate_judged(
    data: dict[str, Any],
    cases_data: dict[str, Any],
    raw_path: Path,
    raw_commit: str,
    raw_case_ids: list[str],
) -> list[dict[str, Any]]:
    require_exact_keys(
        data,
        {"schemaVersion", "kind", "source", "judge", "rawSha256", "judgments"},
        "judged",
    )
    if data["schemaVersion"] != SCHEMA_VERSION or data["kind"] != JUDGED_KIND:
        raise ValidationError("judgedのschemaVersionまたはkindが対応スキーマと一致しません")
    judged_commit = validate_source(data["source"], cases_data, "judged.source")
    if judged_commit != raw_commit:
        raise ValidationError("rawとjudgedのsourceCommitが一致しません")
    validate_identity(data["judge"], "judged.judge")
    recorded_raw_hash = require_nonempty_string(data["rawSha256"], "judged.rawSha256")
    if recorded_raw_hash != file_sha256(raw_path):
        raise ValidationError("judged.rawSha256がrawファイルと一致しません")
    if not isinstance(data["judgments"], list):
        raise ValidationError("judged.judgmentsは配列でなければなりません")

    judgments: list[dict[str, Any]] = []
    seen: set[str] = set()
    for index, judgment in enumerate(data["judgments"]):
        label = f"judged.judgments[{index}]"
        if not isinstance(judgment, dict):
            raise ValidationError(f"{label}はオブジェクトでなければなりません")
        require_exact_keys(judgment, {"caseId", "checks", "notes"}, label)
        case_id = require_nonempty_string(judgment["caseId"], f"{label}.caseId")
        if case_id in seen:
            raise ValidationError(f"judgmentsのcaseIdが重複しています: {case_id}")
        seen.add(case_id)
        if not isinstance(judgment["checks"], dict):
            raise ValidationError(f"{label}.checksはオブジェクトでなければなりません")
        require_exact_keys(judgment["checks"], set(CHECK_NAMES), f"{label}.checks")
        for check_name, status in judgment["checks"].items():
            if status not in STATUSES:
                raise ValidationError(
                    f"{label}.checks.{check_name}はpass/fail/not-applicableのいずれかです"
                )
        if not isinstance(judgment["notes"], str):
            raise ValidationError(f"{label}.notesは文字列でなければなりません")
        judgments.append(judgment)

    if set(seen) != set(raw_case_ids) or len(judgments) != len(raw_case_ids):
        raise ValidationError("judgmentsのcaseIdはraw.outputsと過不足なく一致させてください")
    return judgments


def summarize(source_commit: str, judgments: list[dict[str, Any]]) -> dict[str, Any]:
    check_counts = {name: Counter() for name in CHECK_NAMES}
    passed_cases = 0
    failed_cases = 0
    for judgment in judgments:
        failed = False
        for name, status in judgment["checks"].items():
            check_counts[name][status] += 1
            failed = failed or status == "fail"
        if failed:
            failed_cases += 1
        else:
            passed_cases += 1

    return {
        "sourceCommit": source_commit,
        "totalCases": len(judgments),
        "passedCases": passed_cases,
        "failedCases": failed_cases,
        "checkCounts": {
            name: {status: check_counts[name][status] for status in sorted(STATUSES)}
            for name in CHECK_NAMES
        },
        "scope": "single-run-pilot-not-a-benchmark",
    }


def main() -> int:
    args = parse_args()
    try:
        raw_path = args.raw.resolve()
        judged_path = args.judged.resolve()
        cases_path = args.cases.resolve()
        cases_data = load_json(cases_path, "cases")
        cases_data["_path"] = str(cases_path)
        if not isinstance(cases_data.get("cases"), list):
            raise ValidationError("cases.casesは配列でなければなりません")
        known_case_ids = {
            require_nonempty_string(case.get("id"), "cases.cases[].id")
            for case in cases_data["cases"]
            if isinstance(case, dict)
        }
        if len(known_case_ids) != len(cases_data["cases"]):
            raise ValidationError("casesのIDが重複しているか、ケースがオブジェクトではありません")

        raw = load_json(raw_path, "raw")
        judged = load_json(judged_path, "judged")
        source_commit, raw_case_ids = validate_raw(raw, cases_data, known_case_ids)
        validate_commit_exists(source_commit)
        if args.expected_source_commit:
            if not COMMIT_RE.fullmatch(args.expected_source_commit):
                raise ValidationError("--expected-source-commitは40桁の小文字16進SHAです")
            if source_commit != args.expected_source_commit:
                raise ValidationError("sourceCommitが--expected-source-commitと一致しません")
        if args.require_all_cases and set(raw_case_ids) != known_case_ids:
            missing = sorted(known_case_ids - set(raw_case_ids))
            raise ValidationError(f"raw.outputsに全ケースがありません: missing={missing}")

        judgments = validate_judged(judged, cases_data, raw_path, source_commit, raw_case_ids)
        print(json.dumps(summarize(source_commit, judgments), ensure_ascii=False, indent=2))
        return 0
    except ValidationError as exc:
        print(f"評価ファイルの検証に失敗しました: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
