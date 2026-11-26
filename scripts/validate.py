#!/usr/bin/env python3
"""Проверяет структуру репозитория, скилла и согласованность версий."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILL_NAME = "anti-neuroslop"
SKILL_DIR = ROOT / "skills" / SKILL_NAME
SKILL_MD = SKILL_DIR / "SKILL.md"
MAX_SKILL_LINES = 500
MAX_DESCRIPTION = 1024

errors: list[str] = []
warnings: list[str] = []


def fail(message: str) -> None:
    errors.append(message)


def warn(message: str) -> None:
    warnings.append(message)


def parse_frontmatter(text: str) -> dict[str, str]:
    if not text.startswith("---\n"):
        fail("SKILL.md: нет frontmatter")
        return {}
    end = text.find("\n---", 4)
    if end == -1:
        fail("SKILL.md: frontmatter не закрыт")
        return {}
    block = text[4:end]
    data: dict[str, str] = {}
    for line in block.splitlines():
        if ":" in line and not line.startswith(" "):
            key, value = line.split(":", 1)
            data[key.strip()] = value.strip().strip('"')
    version = re.search(r"^\s{2}version:\s*(\S+)\s*$", block, re.MULTILINE)
    if version:
        data["version"] = version.group(1)
    return data


def check_skill() -> None:
    if not SKILL_MD.is_file():
        fail("нет skills/anti-neuroslop/SKILL.md")
        return
    text = SKILL_MD.read_text(encoding="utf-8")
    meta = parse_frontmatter(text)

    if meta.get("name") != SKILL_NAME:
        fail(f"name в frontmatter: «{meta.get('name')}», ожидалось «{SKILL_NAME}»")

    description = meta.get("description", "")
    if len(description) < 50:
        fail("description короче 50 символов")
    if len(description) > MAX_DESCRIPTION:
        fail(f"description длиннее {MAX_DESCRIPTION} символов: {len(description)}")

    if not re.fullmatch(r"\d+\.\d+\.\d+", meta.get("version", "")):
        fail(f"version не semver: {meta.get('version')!r}")

    lines = text.count("\n") + 1
    if lines > MAX_SKILL_LINES:
        fail(f"SKILL.md длиннее {MAX_SKILL_LINES} строк: {lines}")
    else:
        print(f"  SKILL.md: {lines} строк")

    check_links(SKILL_MD, text)


def check_links(path: Path, text: str) -> None:
    for match in re.finditer(r"\[[^\]]*\]\(([^)]+)\)", text):
        target = match.group(1).split("#", 1)[0].strip()
        if not target or target.startswith(("http://", "https://", "mailto:")):
            continue
        resolved = (path.parent / target).resolve()
        if not resolved.exists():
            fail(f"{path.relative_to(ROOT)}: битая ссылка {target}")


def check_references() -> None:
    refs = SKILL_DIR / "references"
    if not refs.is_dir():
        fail("нет папки references")
        return
    for path in sorted(refs.glob("*.md")):
        text = path.read_text(encoding="utf-8")
        check_links(path, text)
    print(f"  references: {len(list(refs.glob('*.md')))} файлов")


def check_katalog() -> None:
    katalog = SKILL_DIR / "references" / "katalog.md"
    if not katalog.is_file():
        fail("нет references/katalog.md")
        return
    numbers = [int(n) for n in re.findall(r"^### (\d+)\.", katalog.read_text(encoding="utf-8"), re.MULTILINE)]
    if not numbers:
        fail("в каталоге не найдено ни одного маркера")
        return
    if numbers != list(range(1, len(numbers) + 1)):
        fail(f"нумерация каталога с пропусками: {numbers[:10]}…")
    print(f"  каталог: {len(numbers)} маркеров")


def check_json() -> None:
    for rel in ("package.json", ".claude-plugin/plugin.json", ".claude-plugin/marketplace.json"):
        path = ROOT / rel
        if not path.is_file():
            fail(f"нет {rel}")
            continue
        try:
            json.loads(path.read_text(encoding="utf-8"))
        except ValueError as exc:
            fail(f"{rel}: невалидный JSON ({exc})")


def check_versions() -> None:
    meta = parse_frontmatter(SKILL_MD.read_text(encoding="utf-8")) if SKILL_MD.is_file() else {}
    expected = meta.get("version")
    if not expected:
        return
    sources: list[tuple[str, str]] = []

    package = ROOT / "package.json"
    if package.is_file():
        sources.append(("package.json", json.loads(package.read_text(encoding="utf-8")).get("version", "")))

    pyproject = ROOT / "cli" / "pyproject.toml"
    if pyproject.is_file():
        match = re.search(r'^version\s*=\s*"([^"]+)"', pyproject.read_text(encoding="utf-8"), re.MULTILINE)
        if match:
            sources.append(("cli/pyproject.toml", match.group(1)))

    plugin = ROOT / ".claude-plugin" / "plugin.json"
    if plugin.is_file():
        sources.append((".claude-plugin/plugin.json", json.loads(plugin.read_text(encoding="utf-8")).get("version", "")))

    marketplace = ROOT / ".claude-plugin" / "marketplace.json"
    if marketplace.is_file():
        data = json.loads(marketplace.read_text(encoding="utf-8"))
        plugins = data.get("plugins", [])
        if plugins:
            sources.append((".claude-plugin/marketplace.json", plugins[0].get("version", "")))

    for name, value in sources:
        if value != expected:
            fail(f"{name}: версия {value!r}, в SKILL.md {expected!r}")


def check_placeholders() -> None:
    for path in ROOT.rglob("*"):
        if not path.is_file() or ".git" in path.parts or "dist" in path.parts:
            continue
        if path.suffix not in {".md", ".py", ".js", ".sh", ".ps1", ".json", ".toml", ".yaml", ".yml", ".cs"}:
            continue
        if path.name == "validate.py":
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for token in ("TODO", "FIXME", "Lorem ipsum"):
            if token in text:
                warn(f"{path.relative_to(ROOT)}: содержит {token}")


def main() -> int:
    print("Проверка MAN")
    check_skill()
    check_references()
    check_katalog()
    check_json()
    check_versions()
    check_placeholders()

    for message in warnings:
        print(f"  ! {message}")
    if errors:
        print()
        for message in errors:
            print(f"  × {message}")
        print(f"\nОшибок: {len(errors)}")
        return 1
    print("\nВсё в порядке")
    return 0


if __name__ == "__main__":
    sys.exit(main())
