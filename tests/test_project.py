from __future__ import annotations

import importlib.util
import json
import re
import shutil
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILL_ROOT = ROOT / "skills" / "no-ai-slop-ja"
SKILL = SKILL_ROOT / "SKILL.md"
OPENAI_YAML = SKILL_ROOT / "agents" / "openai.yaml"
CASES = ROOT / "tests" / "cases.json"
LINK_RE = re.compile(r"(?<!!)\[[^\]]+\]\(([^)]+)\)")
PATTERN_HEADING_RE = re.compile(r"(?m)^### (\d+)\. (.+)$")


def load_build_module():
    spec = importlib.util.spec_from_file_location("build_plugin", ROOT / "scripts" / "build_plugin.py")
    if spec is None or spec.loader is None:
        raise RuntimeError("build_plugin.pyを読み込めません")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def parse_simple_interface_yaml(text: str) -> dict[str, str]:
    values: dict[str, str] = {}
    lines = text.splitlines()
    if not lines or lines[0] != "interface:":
        raise AssertionError("openai.yamlはinterfaceから始めてください")
    for line in lines[1:]:
        match = re.fullmatch(r"  ([a-z_]+): \"(.*)\"", line)
        if not match:
            raise AssertionError(f"解析できないopenai.yaml行: {line}")
        values[match.group(1)] = match.group(2)
    return values


class ProjectTests(unittest.TestCase):
    def test_required_structure(self) -> None:
        required = [
            SKILL,
            SKILL_ROOT / "eval.md",
            OPENAI_YAML,
            ROOT / "README.md",
            ROOT / "LICENSE",
            ROOT / "NOTICE",
            ROOT / "PRIVACY.md",
            ROOT / "TERMS.md",
            ROOT / ".codex-plugin" / "plugin.json",
            ROOT / "assets" / "no-ai-slop-ja.png",
            ROOT / "examples" / "edit.md",
            ROOT / "examples" / "detect.md",
            CASES,
            ROOT / "tests" / "evaluation" / "README.md",
            ROOT / "scripts" / "validate_evaluation.py",
        ]
        self.assertEqual([], [str(path.relative_to(ROOT)) for path in required if not path.is_file()])
        self.assertFalse((ROOT / "agents").exists(), "OpenAIメタデータをルートagents/へ置かないでください")

    def test_skill_metadata_and_length(self) -> None:
        text = SKILL.read_text(encoding="utf-8")
        self.assertLess(len(text.splitlines()), 500)
        match = re.match(r"\A---\n(.*?)\n---\n", text, re.DOTALL)
        self.assertIsNotNone(match, "SKILL.mdにYAML frontmatterが必要です")
        metadata = {}
        for line in match.group(1).splitlines():
            key, separator, value = line.partition(":")
            self.assertTrue(separator and key and value.strip(), f"不正なメタデータ行: {line}")
            metadata[key] = value.strip()
        self.assertEqual("no-ai-slop-ja", metadata.get("name"))
        self.assertLessEqual(len(metadata.get("name", "")), 64)
        self.assertRegex(metadata["name"], r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
        self.assertLessEqual(len(metadata.get("description", "")), 1024)
        self.assertIn("使う", metadata["description"])
        self.assertIn("使わない", metadata["description"])

    def test_skill_defines_exactly_21_numbered_patterns(self) -> None:
        text = SKILL.read_text(encoding="utf-8")
        headings = [(int(number), name) for number, name in PATTERN_HEADING_RE.findall(text)]
        self.assertEqual(list(range(1, 22)), [number for number, _ in headings])
        self.assertEqual(21, len({name for _, name in headings}))
        self.assertEqual(21, text.count("- 悪い例:"))
        self.assertEqual(21, text.count("- 修正:"))
        self.assertEqual(21, text.count("- 誤検知に注意:"))

    def test_corrections_do_not_use_known_invented_facts(self) -> None:
        text = SKILL.read_text(encoding="utf-8")
        invented_examples = [
            "運営チームが新しい方針",
            "既存の顧客データ",
            "調査結果の整理と出典確認",
            "権限の棚卸しを毎月",
            "管理者が権限を承認",
            "履歴をCSVで出力",
        ]
        for phrase in invented_examples:
            self.assertNotIn(phrase, text)
        for phrase in ("書き手に確認", "分からなければ", "本文の別の箇所"):
            self.assertIn(phrase, text)

    def test_eval_separates_modes(self) -> None:
        text = (SKILL_ROOT / "eval.md").read_text(encoding="utf-8")
        self.assertIn("## 改稿モード", text)
        self.assertIn("## 検出モード", text)
        self.assertIn("AIによる執筆", text)

    def test_case_schema_and_complete_pattern_coverage(self) -> None:
        data = json.loads(CASES.read_text(encoding="utf-8"))
        self.assertEqual(2, data["schemaVersion"])
        self.assertIs(data["modelExecution"], False)
        self.assertIn("宣言的", data["description"])
        self.assertIn("言語モデルの実行結果ではない", data["description"])

        skill_patterns = [
            {"number": int(number), "name": name}
            for number, name in PATTERN_HEADING_RE.findall(SKILL.read_text(encoding="utf-8"))
        ]
        self.assertEqual(skill_patterns, data["patterns"])
        known_patterns = {entry["name"] for entry in data["patterns"]}

        ids: set[str] = set()
        covered: set[str] = set()
        categories: dict[str, int] = {}
        for case in data["cases"]:
            for field in ("id", "category", "mode", "input", "expectedPatterns"):
                self.assertIn(field, case, f"{case.get('id', '<unknown>')}に{field}がありません")
            self.assertNotIn(case["id"], ids)
            ids.add(case["id"])
            self.assertIn(case["mode"], {"edit", "detect"})
            self.assertIsInstance(case["input"], str)
            self.assertTrue(case["input"].strip())
            self.assertIsInstance(case["expectedPatterns"], list)
            self.assertTrue(set(case["expectedPatterns"]).issubset(known_patterns))
            categories[case["category"]] = categories.get(case["category"], 0) + 1

            if case["category"] == "positive":
                self.assertTrue(case["expectedPatterns"], case["id"])
                covered.update(case["expectedPatterns"])
            elif case["category"] == "counterexample":
                self.assertEqual([], case["expectedPatterns"])
                self.assertTrue(case.get("forbiddenPatterns"), case["id"])
                self.assertTrue(set(case["forbiddenPatterns"]).issubset(known_patterns))
            elif case["category"] == "preservation":
                self.assertEqual([], case["expectedPatterns"])
                self.assertTrue(case.get("mustPreserve"), case["id"])
            elif case["category"] == "authorship-refusal":
                self.assertEqual([], case["expectedPatterns"])
                self.assertTrue(case.get("expectedResponse"), case["id"])
                self.assertTrue(case.get("forbiddenOutput"), case["id"])
            else:
                self.fail(f"未知のcategory: {case['category']}")

        self.assertEqual(known_patterns, covered)
        self.assertGreaterEqual(categories.get("positive", 0), 21)
        self.assertGreaterEqual(categories.get("counterexample", 0), 5)
        self.assertGreaterEqual(categories.get("preservation", 0), 3)
        self.assertEqual(1, categories.get("authorship-refusal", 0))

    def test_plugin_and_openai_metadata(self) -> None:
        manifest = json.loads((ROOT / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8"))
        self.assertEqual("no-ai-slop-ja", manifest["name"])
        self.assertEqual("https://github.com/53able/no-ai-slop-ja", manifest["repository"])
        self.assertEqual("53able", manifest["author"]["name"])

        values = parse_simple_interface_yaml(OPENAI_YAML.read_text(encoding="utf-8"))
        self.assertEqual({"display_name", "short_description", "default_prompt"}, set(values))
        self.assertEqual("No AI Slop JA", values["display_name"])
        self.assertLessEqual(len(values["display_name"]), 32)
        self.assertGreaterEqual(len(values["short_description"]), 25)
        self.assertLessEqual(len(values["short_description"]), 64)
        self.assertIn("$no-ai-slop-ja", values["default_prompt"])

    def test_plugin_package_includes_nested_openai_metadata(self) -> None:
        module = load_build_module()
        destinations = {str(destination) for _, destination in module.PACKAGE_FILES}
        self.assertIn("skills/no-ai-slop-ja/agents/openai.yaml", destinations)
        self.assertNotIn("agents/openai.yaml", destinations)
        self.assertTrue(all(source.is_file() for source, _ in module.PACKAGE_FILES))

    def test_clean_skill_installation_layout_without_network(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            installed = Path(directory) / "no-ai-slop-ja"
            shutil.copytree(SKILL_ROOT, installed)
            self.assertTrue((installed / "SKILL.md").is_file())
            self.assertTrue((installed / "eval.md").is_file())
            self.assertTrue((installed / "agents" / "openai.yaml").is_file())
            skill_text = (installed / "SKILL.md").read_text(encoding="utf-8")
            self.assertNotRegex(skill_text, r"/(?:Users|home)/[^\s]+")
            self.assertIn("`eval.md`", skill_text)

    def test_relative_markdown_links_exist(self) -> None:
        failures = []
        for path in ROOT.rglob("*.md"):
            if ".git" in path.parts or ".pi-subagents" in path.parts:
                continue
            text = path.read_text(encoding="utf-8")
            for raw_target in LINK_RE.findall(text):
                target = raw_target.split("#", 1)[0].strip()
                if not target or target.startswith(("http://", "https://", "mailto:")):
                    continue
                resolved = (path.parent / target).resolve()
                if not resolved.exists():
                    failures.append(f"{path.relative_to(ROOT)} -> {raw_target}")
        self.assertEqual([], failures)

    def test_no_local_paths_or_stale_machine_identifiers(self) -> None:
        ignored_parts = {".git", ".pi-subagents", "dist", "__pycache__"}
        text_files = [
            path for path in ROOT.rglob("*")
            if path.is_file()
            and not ignored_parts.intersection(path.parts)
            and path.suffix in {".md", ".json", ".yaml", ".py"}
        ]
        for path in text_files:
            text = path.read_text(encoding="utf-8")
            self.assertNotRegex(text, r"/(?:Users|home)/[^\s]+", str(path))
        machine_files = [ROOT / ".codex-plugin" / "plugin.json", OPENAI_YAML, SKILL]
        stale = [r'"name"\s*:\s*"no-ai-slop"', r"skills/no-ai-slop/", r"(?<!-ja)/no-ai-slop(?:\s|\")"]
        for path in machine_files:
            text = path.read_text(encoding="utf-8")
            for pattern in stale:
                self.assertNotRegex(text, pattern, f"古い識別子: {path.relative_to(ROOT)}")

    def test_readme_scopes_invocation_by_product(self) -> None:
        text = (ROOT / "README.md").read_text(encoding="utf-8")
        for heading in ("### 汎用インストーラー", "### ChatGPT", "### Codex", "### Claude Code"):
            self.assertIn(heading, text)
        for url in (
            "https://learn.chatgpt.com/docs/build-skills",
            "https://code.claude.com/docs/en/skills",
        ):
            self.assertIn(url, text)
        readme_without_metadata_path = text.replace("skills/no-ai-slop-ja/agents/openai.yaml", "")
        self.assertNotIn("$no-ai-slop-ja", readme_without_metadata_path)
        self.assertIn("PromptScript does not support global skill installation", text)
        self.assertIn("-a promptscript", text)
        self.assertIn("https://github.com/vercel-labs/skills/blob/main/src/agents.ts", text)
        self.assertIn("言語モデルを実行して出力品質を測るものではありません", text)

    def test_license_and_notice_preserve_attribution(self) -> None:
        license_text = (ROOT / "LICENSE").read_text(encoding="utf-8")
        notice = (ROOT / "NOTICE").read_text(encoding="utf-8")
        self.assertIn("Copyright (c) 2026 Peter Yang", license_text)
        self.assertIn("Copyright (c) 2026 53able contributors", license_text)
        self.assertIn("d30eddb9e04562234f2070b5ee63ca4649d9a05e", notice)
        self.assertIn("https://github.com/petergyang/no-ai-slop", notice)

    def test_png_signature_and_size(self) -> None:
        icon = (ROOT / "assets" / "no-ai-slop-ja.png").read_bytes()
        self.assertTrue(icon.startswith(b"\x89PNG\r\n\x1a\n"))
        self.assertGreater(len(icon), 100)

    def test_workflow_is_read_only_and_pinned(self) -> None:
        text = (ROOT / ".github" / "workflows" / "validate.yml").read_text(encoding="utf-8")
        self.assertRegex(text, r"(?m)^permissions:\n  contents: read$")
        uses = re.findall(r"uses:\s+([^\s]+)", text)
        self.assertTrue(uses)
        for action in uses:
            self.assertRegex(action, r"^[^@]+@[0-9a-f]{40}$")
        self.assertIn("actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1", text)

    def test_subagent_artifacts_are_ignored_and_untracked(self) -> None:
        gitignore = (ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()
        self.assertIn(".pi-subagents/", gitignore)


if __name__ == "__main__":
    unittest.main()
