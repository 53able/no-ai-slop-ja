from __future__ import annotations

import hashlib
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "validate_evaluation.py"
CASES = ROOT / "tests" / "cases.json"
SKILL = ROOT / "skills" / "no-ai-slop-ja" / "SKILL.md"
EVAL = SKILL.parent / "eval.md"
PROTOCOL = ROOT / "tests" / "evaluation" / "README.md"


def load_evaluation_module():
    spec = importlib.util.spec_from_file_location("validate_evaluation", SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError("validate_evaluation.pyを読み込めません")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class EvaluationInfrastructureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.module = load_evaluation_module()
        cls.commit = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        cls.source = {
            "sourceCommit": cls.commit,
            "skillPath": "skills/no-ai-slop-ja/SKILL.md",
            "skillSha256": sha256(SKILL),
            "casesPath": "tests/cases.json",
            "casesSha256": sha256(CASES),
            "casesSchemaVersion": 2,
        }

    def raw_data(self) -> dict:
        return {
            "schemaVersion": 1,
            "kind": self.module.RAW_KIND,
            "source": self.source,
            "runner": {"identity": "test-runner", "model": "test-model"},
            "promptConstruction": self.module.PROMPT_CONSTRUCTION,
            "outputs": [
                {"caseId": "p01-passive-hidden-actor", "output": "テスト出力1"},
                {"caseId": "p02-koto-shell", "output": "テスト出力2"},
            ],
        }

    def judged_data(self, raw_path: Path, fail_second: bool = False) -> dict:
        judgments = []
        for index, case_id in enumerate(("p01-passive-hidden-actor", "p02-koto-shell")):
            checks = {name: "pass" for name in self.module.CHECK_NAMES}
            checks["quotes"] = "not-applicable"
            checks["sources"] = "not-applicable"
            if fail_second and index == 1:
                checks["modality"] = "fail"
            judgments.append({"caseId": case_id, "checks": checks, "notes": "テスト判定"})
        return {
            "schemaVersion": 1,
            "kind": self.module.JUDGED_KIND,
            "source": self.source,
            "judge": {"identity": "test-judge", "model": "test-model"},
            "rawSha256": sha256(raw_path),
            "judgments": judgments,
        }

    def test_priority_order_and_invariants_are_explicit(self) -> None:
        skill_text = SKILL.read_text(encoding="utf-8")
        meaning = skill_text.index("1. **意味を守る。**")
        ambiguity = skill_text.index("2. **誤読を防ぐ。**")
        formula = skill_text.index("3. **定型感を減らす。**")
        self.assertLess(meaning, ambiguity)
        self.assertLess(ambiguity, formula)
        self.assertIn("下位の優先事項のために、上位の優先事項を損なってはならない", skill_text)
        self.assertIn("命題、モダリティ、確度を変更してはならない", skill_text)

        eval_text = EVAL.read_text(encoding="utf-8")
        for term in (
            "主体",
            "行為",
            "時制・相",
            "モダリティ",
            "確度",
            "因果関係",
            "数値",
            "引用",
            "出典",
        ):
            self.assertIn(term, eval_text)

    def test_protocol_documents_provenance_and_limits(self) -> None:
        text = PROTOCOL.read_text(encoding="utf-8")
        for term in (
            "source commit",
            "runner",
            "model",
            "SKILL.md の全文",
            "cases.json の全文",
            "未加工",
            "独立",
            "意味の不変条件",
            "一般化しません",
            "ベンチマークではありません",
        ):
            self.assertIn(term, text)
        root_readme = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("tests/evaluation/README.md", root_readme)
        self.assertIn("scripts/validate_evaluation.py", root_readme)

    def test_valid_files_are_summarized_from_judgments(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            raw_path = Path(directory) / "raw.json"
            judged_path = Path(directory) / "judged.json"
            raw_path.write_text(json.dumps(self.raw_data(), ensure_ascii=False), encoding="utf-8")
            judged_path.write_text(
                json.dumps(self.judged_data(raw_path, fail_second=True), ensure_ascii=False),
                encoding="utf-8",
            )
            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--raw",
                    str(raw_path),
                    "--judged",
                    str(judged_path),
                    "--expected-source-commit",
                    self.commit,
                ],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(0, result.returncode, result.stderr)
            summary = json.loads(result.stdout)
            self.assertEqual(2, summary["totalCases"])
            self.assertEqual(1, summary["passedCases"])
            self.assertEqual(1, summary["failedCases"])
            self.assertEqual(1, summary["checkCounts"]["modality"]["fail"])
            self.assertEqual("single-run-pilot-not-a-benchmark", summary["scope"])

    def test_unknown_case_id_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            raw_path = Path(directory) / "raw.json"
            judged_path = Path(directory) / "judged.json"
            raw = self.raw_data()
            raw["outputs"][0]["caseId"] = "not-a-real-case"
            raw_path.write_text(json.dumps(raw, ensure_ascii=False), encoding="utf-8")
            judged_path.write_text(
                json.dumps(self.judged_data(raw_path), ensure_ascii=False), encoding="utf-8"
            )
            result = subprocess.run(
                [sys.executable, str(SCRIPT), "--raw", str(raw_path), "--judged", str(judged_path)],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(2, result.returncode)
            self.assertIn("未知のcaseId", result.stderr)

    def test_raw_hash_mismatch_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            raw_path = Path(directory) / "raw.json"
            judged_path = Path(directory) / "judged.json"
            raw_path.write_text(json.dumps(self.raw_data(), ensure_ascii=False), encoding="utf-8")
            judged = self.judged_data(raw_path)
            judged["rawSha256"] = "0" * 64
            judged_path.write_text(json.dumps(judged, ensure_ascii=False), encoding="utf-8")
            result = subprocess.run(
                [sys.executable, str(SCRIPT), "--raw", str(raw_path), "--judged", str(judged_path)],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(2, result.returncode)
            self.assertIn("rawファイルと一致しません", result.stderr)

    def test_schema_and_source_commit_mismatches_are_rejected(self) -> None:
        for mutation, expected_message in (
            (lambda raw: raw.update(schemaVersion=99), "schemaVersion"),
            (
                lambda raw: raw["source"].update(sourceCommit="0" * 40),
                "sourceCommitがこのリポジトリに存在しません",
            ),
        ):
            with self.subTest(expected_message=expected_message), tempfile.TemporaryDirectory() as directory:
                raw_path = Path(directory) / "raw.json"
                judged_path = Path(directory) / "judged.json"
                raw = self.raw_data()
                raw["source"] = dict(raw["source"])
                mutation(raw)
                raw_path.write_text(json.dumps(raw, ensure_ascii=False), encoding="utf-8")
                judged_path.write_text(
                    json.dumps(self.judged_data(raw_path), ensure_ascii=False), encoding="utf-8"
                )
                result = subprocess.run(
                    [sys.executable, str(SCRIPT), "--raw", str(raw_path), "--judged", str(judged_path)],
                    cwd=ROOT,
                    capture_output=True,
                    text=True,
                    check=False,
                )
                self.assertEqual(2, result.returncode)
                self.assertIn(expected_message, result.stderr)

    def test_cli_help_describes_non_generating_behavior(self) -> None:
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "--help"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(0, result.returncode)
        self.assertIn("結果を生成・補完しません", result.stdout)
        self.assertIn("--require-all-cases", result.stdout)


if __name__ == "__main__":
    unittest.main()
