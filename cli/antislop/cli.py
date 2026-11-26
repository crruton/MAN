"""Командная строка antislop."""

from __future__ import annotations

import argparse
import sys
from typing import Optional, Sequence

from . import __version__, installer

OK = "✓"
ARROW = "→"
WARN = "!"
ERR = "×"

NEXT_STEPS = """
Что дальше:
  • Claude Code: /anti-neuroslop или фраза «проверь текст на нейрослоп»
  • OpenCode, Codex: попросите «перепиши, чтобы не пахло GPT»
  • Проверить установку: antislop doctor
"""


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="antislop",
        description="MAN — My Anti-Neuroslop: установка скилла, который находит и переписывает нейрослоп.",
    )
    parser.add_argument("--version", action="version", version=f"antislop {__version__}")
    sub = parser.add_subparsers(dest="command")

    install = sub.add_parser("install", help="установить скилл")
    _target_args(install)
    install.add_argument("--force", action="store_true", help="перезаписать уже установленную версию")
    install.add_argument("--source", help="папка скилла или клона репозитория (офлайн-установка)")
    install.add_argument("--release", help="тег релиза, например v1.0.0 (по умолчанию последний)")
    install.add_argument("--dry-run", action="store_true", help="показать план без изменений")

    uninstall = sub.add_parser("uninstall", help="удалить скилл")
    _target_args(uninstall)
    uninstall.add_argument("--force", action="store_true", help="удалить даже без манифеста")
    uninstall.add_argument("--dry-run", action="store_true", help="показать план без изменений")

    sub.add_parser("doctor", help="показать найденных агентов и установленные версии")
    sub.add_parser("version", help="версия antislop и окружение")
    return parser


def _target_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--target",
        default="auto",
        choices=["auto", "all", "claude", "opencode", "codex"],
        help="куда ставить (по умолчанию auto — найденные агенты)",
    )
    parser.add_argument(
        "--scope",
        default="user",
        choices=["user", "project"],
        help="личные скиллы или скиллы проекта (по умолчанию user)",
    )
    parser.add_argument("--dir", help="своя папка скиллов, перекрывает --target и --scope")


def main(argv: Optional[Sequence[str]] = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass
    parser = build_parser()
    args = parser.parse_args(argv)

    if not args.command:
        parser.print_help()
        return 0

    try:
        if args.command == "install":
            return _install(args)
        if args.command == "uninstall":
            return _uninstall(args)
        if args.command == "doctor":
            return _doctor()
        if args.command == "version":
            return _version()
    except installer.InstallError as exc:
        print(f"{ERR} {exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print(f"\n{WARN} прервано", file=sys.stderr)
        return 130
    return 0


def _install(args: argparse.Namespace) -> int:
    targets = installer.resolve_targets(args.target, args.scope, args.dir)
    if args.source:
        source = "локальная папка"
    elif installer.local_checkout() is not None:
        source = "локальный клон репозитория"
    elif args.release:
        source = f"релиз {args.release}"
    else:
        source = "последний релиз GitHub"
    print(f"{ARROW} Источник: {source}")
    for target in targets:
        print(f"{ARROW} Цель: {target}")
    if args.dry_run:
        print(f"{WARN} режим проверки: файлы не изменяются")
    installed = installer.install(
        target=args.target,
        scope=args.scope,
        directory=args.dir,
        force=args.force,
        source=args.source,
        version=args.release,
        dry_run=args.dry_run,
    )
    for path in installed:
        if args.dry_run:
            print(f"{OK} будет установлено: {path}")
        else:
            version = installer.installed_version(path)
            print(f"{OK} установлено: {path} ({version})")
    if not args.dry_run:
        print(NEXT_STEPS)
    return 0


def _uninstall(args: argparse.Namespace) -> int:
    removed = installer.uninstall(
        target=args.target,
        scope=args.scope,
        directory=args.dir,
        force=args.force,
        dry_run=args.dry_run,
    )
    if not removed:
        print(f"{WARN} скилл не найден — удалять нечего")
        return 0
    for path in removed:
        verb = "будет удалено" if args.dry_run else "удалено"
        print(f"{OK} {verb}: {path}")
    return 0


def _doctor() -> int:
    rows = installer.doctor()
    width_agent = max(len(str(row["agent"])) for row in rows)
    print(f"{'Агент':<{width_agent}}  {'Найден':<7}  Версия   Путь")
    print("-" * (width_agent + 8 + 9 + 8 + 40))
    for row in rows:
        found = "да" if row["detected"] else "нет"
        version = row["version"] or "—"
        print(f"{row['agent']:<{width_agent}}  {found:<7}  {version:<8} {row['path']}")
    print()
    env = installer.environment()
    print(f"antislop {env['antislop']} · Python {env['python']} · {env['os']} · {env['arch']}")
    if not any(row["detected"] for row in rows):
        print(f"{WARN} ни один агент не найден. Установите вручную: antislop install --dir <папка>")
    return 0


def _version() -> int:
    env = installer.environment()
    print(f"antislop {env['antislop']}")
    print(f"Python {env['python']} · {env['os']} · {env['arch']}")
    print(f"Репозиторий: https://github.com/{installer.REPO}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
