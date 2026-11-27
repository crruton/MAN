"""Тесты установщика antislop. Запуск: python -m unittest discover -s tests"""

from __future__ import annotations

import io
import json
import sys
import tarfile
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "cli"))

from antislop import installer  # noqa: E402

SKILL_SOURCE = ROOT / "skills" / installer.SKILL_NAME


def make_skill(root: Path, version: str = "9.9.9") -> Path:
    skill = root / installer.SKILL_NAME
    (skill / "references").mkdir(parents=True)
    (skill / "SKILL.md").write_text(
        "---\n"
        f"name: {installer.SKILL_NAME}\n"
        "description: тестовый скилл\n"
        "metadata:\n"
        f"  version: {version}\n"
        "---\n\n"
        "# Тест\n",
        encoding="utf-8",
    )
    (skill / "references" / "katalog.md").write_text("# Каталог\n", encoding="utf-8")
    return skill


class VersionTests(unittest.TestCase):
    def test_reads_version_from_frontmatter(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            skill = make_skill(Path(tmp), "1.2.3")
            self.assertEqual(installer.read_version(skill), "1.2.3")

    def test_missing_skill_md_returns_unknown(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(installer.read_version(Path(tmp)), "unknown")

    def test_installed_version_prefers_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            skill = make_skill(Path(tmp), "1.2.3")
            (skill / installer.MANIFEST).write_text(
                json.dumps({"version": "4.5.6"}), encoding="utf-8"
            )
            self.assertEqual(installer.installed_version(skill), "4.5.6")


class LocateTests(unittest.TestCase):
    def test_directory_with_skill(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            skill = make_skill(Path(tmp))
            self.assertEqual(installer.locate_skill(skill), skill)

    def test_path_to_skill_md(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            skill = make_skill(Path(tmp))
            self.assertEqual(installer.locate_skill(skill / "SKILL.md"), skill)

    def test_nested_repository_layout(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            (repo / "skills").mkdir(parents=True)
            skill = make_skill(repo / "skills")
            self.assertEqual(installer.locate_skill(repo), skill)

    def test_directory_without_skill_raises(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(installer.InstallError):
                installer.locate_skill(Path(tmp))


class InstallTests(unittest.TestCase):
    def test_install_writes_files_and_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "skills"
            installed = installer.install(
                directory=str(target), force=True, source=str(SKILL_SOURCE)
            )
            self.assertEqual(installed, [target / installer.SKILL_NAME])
            skill = target / installer.SKILL_NAME
            self.assertTrue((skill / "SKILL.md").is_file())
            self.assertTrue((skill / "references" / "katalog.md").is_file())
            manifest = json.loads((skill / installer.MANIFEST).read_text(encoding="utf-8"))
            self.assertEqual(manifest["skill"], installer.SKILL_NAME)
            self.assertIn("SKILL.md", manifest["files"])
            self.assertNotIn(installer.MANIFEST, manifest["files"])

    def test_install_refuses_existing_without_force(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            installer.install(directory=tmp, force=True, source=str(SKILL_SOURCE))
            with self.assertRaises(installer.InstallError):
                installer.install(directory=tmp, source=str(SKILL_SOURCE))

    def test_install_force_replaces_existing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / installer.SKILL_NAME
            target.mkdir(parents=True)
            (target / "SKILL.md").write_text("old", encoding="utf-8")
            (target / "stale.txt").write_text("stale", encoding="utf-8")
            installer.install(directory=tmp, force=True, source=str(SKILL_SOURCE))
            self.assertFalse((target / "stale.txt").exists())
            self.assertNotEqual((target / "SKILL.md").read_text(encoding="utf-8"), "old")

    def test_dry_run_creates_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "skills"
            installer.install(
                directory=str(target), force=True, source=str(SKILL_SOURCE), dry_run=True
            )
            self.assertFalse(target.exists())

    def test_install_rejects_directory_without_skill_md(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / installer.SKILL_NAME
            target.mkdir()
            (target / "notes.txt").write_text("x", encoding="utf-8")
            with self.assertRaises(installer.InstallError):
                installer.install(directory=tmp, force=True, source=str(SKILL_SOURCE))


class UninstallTests(unittest.TestCase):
    def test_uninstall_removes_installed_skill(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            installer.install(directory=tmp, force=True, source=str(SKILL_SOURCE))
            removed = installer.uninstall(directory=tmp)
            self.assertEqual(removed, [Path(tmp) / installer.SKILL_NAME])
            self.assertFalse((Path(tmp) / installer.SKILL_NAME).exists())

    def test_uninstall_without_manifest_requires_force(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / installer.SKILL_NAME
            target.mkdir(parents=True)
            (target / "SKILL.md").write_text("x", encoding="utf-8")
            with self.assertRaises(installer.InstallError):
                installer.uninstall(directory=tmp)
            self.assertTrue(target.exists())
            installer.uninstall(directory=tmp, force=True)
            self.assertFalse(target.exists())

    def test_uninstall_keeps_foreign_files_outside_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            installer.install(directory=tmp, force=True, source=str(SKILL_SOURCE))
            skill = Path(tmp) / installer.SKILL_NAME
            extra = skill / "my-notes.md"
            extra.write_text("моё", encoding="utf-8")
            installer.uninstall(directory=tmp)
            self.assertTrue(extra.is_file())

    def test_uninstall_removes_shell_install_with_empty_file_list(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            skill = make_skill(Path(tmp))
            (skill / installer.MANIFEST).write_text(
                json.dumps({"version": "1.0.0", "files": []}), encoding="utf-8"
            )
            installer.uninstall(directory=tmp)
            self.assertFalse(skill.exists())

    def test_uninstall_missing_skill_is_noop(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(installer.uninstall(directory=tmp), [])


class ChecksumTests(unittest.TestCase):
    def test_matching_checksum_passes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            archive = Path(tmp) / "man-skill.tar.gz"
            archive.write_bytes(b"payload")
            sums = Path(tmp) / "SHA256SUMS.txt"
            sums.write_text(
                f"{installer.sha256(archive)}  man-skill.tar.gz\n", encoding="utf-8"
            )
            installer.verify_checksum(archive, sums)

    def test_mismatched_checksum_raises(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            archive = Path(tmp) / "man-skill.tar.gz"
            archive.write_bytes(b"payload")
            sums = Path(tmp) / "SHA256SUMS.txt"
            sums.write_text("0" * 64 + "  man-skill.tar.gz\n", encoding="utf-8")
            with self.assertRaises(installer.InstallError):
                installer.verify_checksum(archive, sums)

    def test_missing_entry_raises(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            archive = Path(tmp) / "man-skill.tar.gz"
            archive.write_bytes(b"payload")
            sums = Path(tmp) / "SHA256SUMS.txt"
            sums.write_text("0" * 64 + "  other.tar.gz\n", encoding="utf-8")
            with self.assertRaises(installer.InstallError):
                installer.verify_checksum(archive, sums)


class ExtractTests(unittest.TestCase):
    def test_extracts_regular_archive(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            archive = Path(tmp) / "skill.tar.gz"
            with tarfile.open(archive, "w:gz") as tar:
                data = b"# Skill\n"
                info = tarfile.TarInfo(f"{installer.SKILL_NAME}/SKILL.md")
                info.size = len(data)
                tar.addfile(info, io.BytesIO(data))
            dest = Path(tmp) / "out"
            installer.extract_tar(archive, dest)
            self.assertTrue((dest / installer.SKILL_NAME / "SKILL.md").is_file())

    def test_rejects_path_traversal(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            archive = Path(tmp) / "evil.tar.gz"
            with tarfile.open(archive, "w:gz") as tar:
                info = tarfile.TarInfo("../evil.txt")
                info.size = 1
                tar.addfile(info, io.BytesIO(b"x"))
            with self.assertRaises(installer.InstallError):
                installer.extract_tar(archive, Path(tmp) / "out")
            self.assertFalse((Path(tmp) / "evil.txt").exists())


class DoctorTests(unittest.TestCase):
    def test_doctor_reports_three_agents(self) -> None:
        rows = installer.doctor()
        self.assertEqual(len(rows), 3)
        self.assertEqual({row["agent"] for row in rows}, {"Claude Code", "OpenCode", "Codex"})
        for row in rows:
            self.assertIn("detected", row)
            self.assertIn("path", row)


if __name__ == "__main__":
    unittest.main()
