"""Логика установки скилла MAN — My Anti-Neuroslop.

Модуль не зависит от CLI: его можно использовать из скриптов и тестов.
"""

from __future__ import annotations

import hashlib
import json
import os
import platform
import re
import shutil
import sys
import tarfile
import tempfile
import time
import urllib.error
import urllib.request
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator, Optional

REPO = "crruton/MAN"
SKILL_NAME = "anti-neuroslop"
MANIFEST = ".man.json"
USER_AGENT = "man-antislop/1.0"


class InstallError(RuntimeError):
    """Ошибка установки, которую нужно показать пользователю без трейсбека."""


@dataclass(frozen=True)
class Agent:
    key: str
    title: str
    user_dir: Path
    project_dir: Path

    @property
    def config_dir(self) -> Path:
        return self.user_dir.parent


def agents() -> list[Agent]:
    home = Path.home()
    cwd = Path.cwd()
    return [
        Agent("claude", "Claude Code", home / ".claude" / "skills", cwd / ".claude" / "skills"),
        Agent("opencode", "OpenCode", home / ".config" / "opencode" / "skills", cwd / ".opencode" / "skills"),
        Agent("codex", "Codex", home / ".codex" / "skills", cwd / ".codex" / "skills"),
    ]


def detected_agents() -> list[Agent]:
    found = [a for a in agents() if a.config_dir.exists()]
    return found or [agents()[0]]


def resolve_targets(
    target: str = "auto",
    scope: str = "user",
    directory: Optional[str] = None,
) -> list[Path]:
    if directory:
        return [Path(directory).expanduser().resolve()]
    if target == "all":
        chosen = agents()
    elif target == "auto":
        chosen = detected_agents()
    else:
        matches = [a for a in agents() if a.key == target]
        if not matches:
            keys = ", ".join(a.key for a in agents())
            raise InstallError(f"неизвестная цель «{target}». Доступно: auto, all, {keys}")
        chosen = matches
    if scope == "project":
        return [a.project_dir.resolve() for a in chosen]
    if scope == "user":
        return [a.user_dir for a in chosen]
    raise InstallError("scope должен быть user или project")


def install(
    target: str = "auto",
    scope: str = "user",
    directory: Optional[str] = None,
    force: bool = False,
    source: Optional[str] = None,
    version: Optional[str] = None,
    dry_run: bool = False,
) -> list[Path]:
    dests = resolve_targets(target, scope, directory)
    installed: list[Path] = []
    with source_skill(source, version) as src:
        for dest in dests:
            path = _install_one(src, dest, force=force, dry_run=dry_run)
            installed.append(path)
    return installed


@contextmanager
def source_skill(source: Optional[str], version: Optional[str]) -> Iterator[Path]:
    if source:
        yield locate_skill(Path(source).expanduser().resolve())
        return
    local = local_checkout()
    if local is not None:
        yield local
        return
    tmp = tempfile.mkdtemp(prefix="man-")
    try:
        yield download_skill(Path(tmp), version)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def local_checkout() -> Optional[Path]:
    """Скилл рядом с пакетом: запуск из клона репозитория."""
    candidate = Path(__file__).resolve().parents[2] / "skills" / SKILL_NAME
    if (candidate / "SKILL.md").is_file():
        return candidate
    return None


def locate_skill(path: Path) -> Path:
    if path.is_file() and path.name == "SKILL.md":
        return path.parent
    if (path / "SKILL.md").is_file():
        return path
    nested = path / "skills" / SKILL_NAME
    if (nested / "SKILL.md").is_file():
        return nested
    raise InstallError(f"в «{path}» нет SKILL.md")


def download_skill(dest: Path, version: Optional[str] = None) -> Path:
    """Скачивает релизный архив скилла и возвращает путь к распакованной папке."""
    api = (
        f"https://api.github.com/repos/{REPO}/releases/tags/{version}"
        if version
        else f"https://api.github.com/repos/{REPO}/releases/latest"
    )
    assets: dict[str, str] = {}
    try:
        release = _json(api)
        assets = {a["name"]: a["browser_download_url"] for a in release.get("assets", [])}
    except urllib.error.HTTPError as exc:
        if exc.code != 404:
            raise InstallError(f"GitHub API вернул {exc.code}") from exc

    archive = dest / "man-skill.tar.gz"
    if "man-skill.tar.gz" in assets:
        _fetch(assets["man-skill.tar.gz"], archive)
        if "SHA256SUMS.txt" in assets:
            sums = dest / "SHA256SUMS.txt"
            _fetch(assets["SHA256SUMS.txt"], sums)
            verify_checksum(archive, sums)
    else:
        url = (
            f"https://github.com/{REPO}/archive/refs/tags/{version}.tar.gz"
            if version
            else f"https://codeload.github.com/{REPO}/tar.gz/refs/heads/main"
        )
        _fetch(url, archive)

    unpacked = dest / "unpacked"
    extract_tar(archive, unpacked)
    for found in sorted(unpacked.rglob("SKILL.md")):
        if found.parent.name == SKILL_NAME:
            return found.parent
    raise InstallError(f"в архиве не найден скилл «{SKILL_NAME}»")


def verify_checksum(archive: Path, sums: Path) -> None:
    expected = None
    for line in sums.read_text(encoding="utf-8").splitlines():
        parts = line.split()
        if len(parts) == 2 and parts[1].lstrip("*") == archive.name:
            expected = parts[0].lower()
            break
    if expected is None:
        raise InstallError(f"в {sums.name} нет контрольной суммы для {archive.name}")
    actual = sha256(archive)
    if actual != expected:
        raise InstallError(
            f"контрольная сумма не совпала: ожидалась {expected[:12]}…, получена {actual[:12]}…"
        )


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 256), b""):
            digest.update(chunk)
    return digest.hexdigest()


def extract_tar(archive: Path, dest: Path) -> None:
    dest.mkdir(parents=True, exist_ok=True)
    with tarfile.open(archive, "r:gz") as tar:
        members = tar.getmembers()
        root = dest.resolve()
        for member in members:
            target = (dest / member.name).resolve()
            if root not in target.parents and target != root:
                raise InstallError(f"архив содержит небезопасный путь: {member.name}")
        try:
            tar.extractall(dest, filter="data")  # Python 3.12+
        except TypeError:
            tar.extractall(dest)


def _install_one(src: Path, dest_dir: Path, force: bool, dry_run: bool) -> Path:
    target = dest_dir / SKILL_NAME
    if target.exists():
        if not force:
            version = installed_version(target) or "неизвестной версии"
            raise InstallError(
                f"скилл уже установлен в {target} ({version}). "
                "Обновите командой install --force или удалите: uninstall"
            )
        if not (target / "SKILL.md").is_file():
            raise InstallError(f"{target} не похож на скилл: нет SKILL.md, удалите вручную")
        if not dry_run:
            shutil.rmtree(target)
    if dry_run:
        return target
    dest_dir.mkdir(parents=True, exist_ok=True)
    shutil.copytree(src, target)
    write_manifest(target, src)
    return target


def write_manifest(target: Path, src: Path) -> None:
    files = sorted(
        str(p.relative_to(target)).replace(os.sep, "/")
        for p in target.rglob("*")
        if p.is_file() and p.name != MANIFEST
    )
    data = {
        "skill": SKILL_NAME,
        "version": read_version(src),
        "installed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "source": "https://github.com/" + REPO,
        "files": files,
    }
    (target / MANIFEST).write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def read_version(skill_dir: Path) -> str:
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.is_file():
        return "unknown"
    text = skill_md.read_text(encoding="utf-8", errors="replace")
    match = re.search(r"^\s{2}version:\s*([^\s]+)\s*$", text, re.MULTILINE)
    return match.group(1) if match else "unknown"


def installed_version(skill_dir: Path) -> Optional[str]:
    manifest = skill_dir / MANIFEST
    if manifest.is_file():
        try:
            return str(json.loads(manifest.read_text(encoding="utf-8")).get("version", "unknown"))
        except (OSError, ValueError):
            return "unknown"
    if (skill_dir / "SKILL.md").is_file():
        return read_version(skill_dir)
    return None


def uninstall(
    target: str = "auto",
    scope: str = "user",
    directory: Optional[str] = None,
    force: bool = False,
    dry_run: bool = False,
) -> list[Path]:
    removed: list[Path] = []
    for dest in resolve_targets(target, scope, directory):
        skill_dir = dest / SKILL_NAME
        if not skill_dir.exists():
            continue
        manifest_path = skill_dir / MANIFEST
        if manifest_path.is_file():
            try:
                files = json.loads(manifest_path.read_text(encoding="utf-8")).get("files", [])
            except (OSError, ValueError):
                files = []
            if dry_run:
                removed.append(skill_dir)
                continue
            root = skill_dir.resolve()
            if not files:
                # Манифест есть, списка файлов нет (установка shell-скриптом):
                # папка принадлежит нам, удаляем целиком.
                shutil.rmtree(skill_dir, ignore_errors=True)
                removed.append(skill_dir)
                continue
            for rel in files:
                candidate = (skill_dir / str(rel)).resolve()
                if root in candidate.parents and candidate.is_file():
                    candidate.unlink(missing_ok=True)
            manifest_path.unlink(missing_ok=True)
            _remove_empty_dirs(skill_dir)
            removed.append(skill_dir)
        elif force:
            if not dry_run:
                shutil.rmtree(skill_dir)
            removed.append(skill_dir)
        else:
            raise InstallError(
                f"в {skill_dir} нет манифеста установки. "
                "Удалите папку вручную или повторите с --force"
            )
    return removed


def _remove_empty_dirs(root: Path) -> None:
    for path in sorted(root.rglob("*"), reverse=True):
        if path.is_dir() and not any(path.iterdir()):
            path.rmdir()
    if root.is_dir() and not any(root.iterdir()):
        root.rmdir()


def doctor() -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for agent in agents():
        skill_dir = agent.user_dir / SKILL_NAME
        rows.append(
            {
                "agent": agent.title,
                "config": str(agent.config_dir),
                "detected": agent.config_dir.exists(),
                "path": str(skill_dir),
                "version": installed_version(skill_dir) if skill_dir.exists() else None,
            }
        )
    return rows


def environment() -> dict[str, str]:
    return {
        "antislop": _package_version(),
        "python": platform.python_version(),
        "os": f"{platform.system()} {platform.release()}",
        "arch": platform.machine(),
    }


def _package_version() -> str:
    try:
        from . import __version__

        return __version__
    except Exception:  # pragma: no cover
        return "unknown"


def _json(url: str) -> dict:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": USER_AGENT, "Accept": "application/vnd.github+json"},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def _fetch(url: str, dest: Path) -> None:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            dest.write_bytes(response.read())
    except urllib.error.HTTPError as exc:
        raise InstallError(f"не удалось скачать {url}: HTTP {exc.code}") from exc
    except urllib.error.URLError as exc:
        raise InstallError(
            f"нет связи с GitHub ({exc.reason}). "
            "Скачайте архив вручную: https://github.com/" + REPO + "/releases"
        ) from exc
