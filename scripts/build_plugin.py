#!/usr/bin/env python3
"""No AI Slop JAの配布用プラグインZIPを構築・検証する。"""

from __future__ import annotations

import argparse
import json
import shutil
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / ".codex-plugin" / "plugin.json"
DIST = ROOT / "dist"
NAME = "no-ai-slop-ja"
SKILL_ROOT = ROOT / "skills" / NAME
ICON = ROOT / "assets" / f"{NAME}.png"

PACKAGE_FILES = (
    (MANIFEST, Path(".codex-plugin/plugin.json")),
    (SKILL_ROOT / "SKILL.md", Path(f"skills/{NAME}/SKILL.md")),
    (SKILL_ROOT / "eval.md", Path(f"skills/{NAME}/eval.md")),
    (SKILL_ROOT / "agents" / "openai.yaml", Path(f"skills/{NAME}/agents/openai.yaml")),
    (ICON, Path(f"assets/{NAME}.png")),
    (ROOT / "LICENSE", Path("LICENSE")),
    (ROOT / "NOTICE", Path("NOTICE")),
    (ROOT / "PRIVACY.md", Path("PRIVACY.md")),
    (ROOT / "TERMS.md", Path("TERMS.md")),
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="構成とZIPを検証し、生成物を残さない",
    )
    return parser.parse_args()


def load_and_validate_manifest() -> dict:
    try:
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SystemExit(f"plugin.jsonを読み込めません: {exc}") from exc

    required = ("name", "version", "description", "author", "repository", "skills", "interface")
    missing = [key for key in required if not manifest.get(key)]
    if missing:
        raise SystemExit(f"plugin.jsonの必須項目がありません: {', '.join(missing)}")
    if manifest["name"] != NAME:
        raise SystemExit(f"plugin.jsonのnameは{NAME}でなければなりません")

    interface = manifest["interface"]
    required_interface = (
        "displayName",
        "shortDescription",
        "longDescription",
        "developerName",
        "category",
        "capabilities",
        "defaultPrompt",
        "composerIcon",
        "logo",
    )
    missing_interface = [key for key in required_interface if not interface.get(key)]
    if missing_interface:
        raise SystemExit(f"interfaceの必須項目がありません: {', '.join(missing_interface)}")

    prompts = interface["defaultPrompt"]
    if not isinstance(prompts, list) or len(prompts) > 3:
        raise SystemExit("defaultPromptは3件以下の配列にしてください")
    if any(not isinstance(prompt, str) or len(prompt) > 128 for prompt in prompts):
        raise SystemExit("各defaultPromptは128文字以下の文字列にしてください")

    missing_files = [str(source.relative_to(ROOT)) for source, _ in PACKAGE_FILES if not source.is_file()]
    if missing_files:
        raise SystemExit(f"配布元ファイルがありません: {', '.join(missing_files)}")
    return manifest


def build(manifest: dict) -> tuple[Path, Path]:
    plugin_root = DIST / NAME
    if plugin_root.exists():
        shutil.rmtree(plugin_root)
    plugin_root.mkdir(parents=True, exist_ok=True)

    for source, destination in PACKAGE_FILES:
        target = plugin_root / destination
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)

    archive = DIST / f"{NAME}-plugin-{manifest['version']}.zip"
    if archive.exists():
        archive.unlink()
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as output:
        for path in sorted(plugin_root.rglob("*")):
            if path.is_file():
                output.write(path, path.relative_to(DIST))
    return plugin_root, archive


def validate_build(plugin_root: Path, archive: Path) -> None:
    expected = {str(destination) for _, destination in PACKAGE_FILES}
    actual = {
        str(path.relative_to(plugin_root))
        for path in plugin_root.rglob("*")
        if path.is_file()
    }
    if actual != expected:
        raise SystemExit(f"ZIPの内容が一致しません: expected={sorted(expected)}, actual={sorted(actual)}")
    if not zipfile.is_zipfile(archive):
        raise SystemExit("生成物は有効なZIPではありません")
    with zipfile.ZipFile(archive) as package:
        archived = {name.removeprefix(f"{NAME}/") for name in package.namelist()}
    if archived != expected:
        raise SystemExit("ZIP内のファイル一覧が期待値と一致しません")


def clean(plugin_root: Path, archive: Path) -> None:
    shutil.rmtree(plugin_root)
    archive.unlink()
    try:
        DIST.rmdir()
    except OSError:
        pass


def main() -> None:
    args = parse_args()
    manifest = load_and_validate_manifest()
    plugin_root, archive = build(manifest)
    validate_build(plugin_root, archive)
    print(f"検証済み: {archive.relative_to(ROOT)}")
    if args.check:
        clean(plugin_root, archive)
        print("--checkのため生成物を削除しました")


if __name__ == "__main__":
    main()
