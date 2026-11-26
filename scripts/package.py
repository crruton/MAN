#!/usr/bin/env python3
"""Собирает релизные архивы скилла: tar.gz, zip и SHA256SUMS."""

from __future__ import annotations

import argparse
import hashlib
import re
import shutil
import tarfile
import time
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILL_NAME = "anti-neuroslop"
SKILL_DIR = ROOT / "skills" / SKILL_NAME
DIST = ROOT / "dist"


def read_version() -> str:
    text = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
    match = re.search(r"^\s{2}version:\s*(\S+)\s*$", text, re.MULTILINE)
    if not match:
        raise SystemExit("не удалось прочитать version из SKILL.md")
    return match.group(1)


def skill_files() -> list[tuple[Path, str]]:
    items: list[tuple[Path, str]] = []
    for path in sorted(SKILL_DIR.rglob("*")):
        if path.is_file() and path.name != ".man.json":
            arc = f"{SKILL_NAME}/{path.relative_to(SKILL_DIR).as_posix()}"
            items.append((path, arc))
    return items


def build_tar(out: Path, mtime: int) -> None:
    with tarfile.open(out, "w:gz") as tar:
        for src, arc in skill_files():
            info = tar.gettarinfo(str(src), arcname=arc)
            info.uid = info.gid = 0
            info.uname = info.gname = "root"
            info.mtime = mtime
            with src.open("rb") as handle:
                tar.addfile(info, handle)


def build_zip(out: Path, mtime: int) -> None:
    stamp = time.localtime(mtime)[:6]
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as archive:
        for src, arc in skill_files():
            info = zipfile.ZipInfo(arc, date_time=stamp)
            info.external_attr = 0o644 << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, src.read_bytes())


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 256), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", help="версия для имён файлов (по умолчанию из SKILL.md)")
    parser.add_argument("--out", default=str(DIST), help="папка для артефактов")
    parser.add_argument("--exe", help="добавить собранный MAN-Setup.exe в релиз")
    args = parser.parse_args()

    version = args.version or read_version()
    out_dir = Path(args.out).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    mtime = int(time.time())

    tar_path = out_dir / "man-skill.tar.gz"
    zip_path = out_dir / "man-skill.zip"
    build_tar(tar_path, mtime)
    build_zip(zip_path, mtime)

    artifacts = [tar_path, zip_path]

    for script in ("install.sh", "install.ps1"):
        source = ROOT / "scripts" / script
        if source.is_file():
            target = out_dir / script
            shutil.copy2(source, target)
            artifacts.append(target)

    if args.exe:
        exe = Path(args.exe).resolve()
        if not exe.is_file():
            raise SystemExit(f"нет файла {exe}")
        target = out_dir / "MAN-Setup.exe"
        if exe != target.resolve():
            shutil.copy2(exe, target)
        artifacts.append(target)

    lines = [f"{sha256(path)}  {path.name}" for path in sorted(artifacts)]
    (out_dir / "SHA256SUMS.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"версия {version}")
    for path in artifacts:
        print(f"  {path.name:<20} {path.stat().st_size:>8} байт")
    print(f"  {'SHA256SUMS.txt':<20} {(out_dir / 'SHA256SUMS.txt').stat().st_size:>8} байт")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
