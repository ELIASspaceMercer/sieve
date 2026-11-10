"""Verify archive contents, reproducibility and exclusion of uncommitted data."""
import hashlib
import importlib.util
from pathlib import Path
import subprocess
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("package_skill", ROOT / "scripts/package_skill.py")
packager = importlib.util.module_from_spec(spec)
spec.loader.exec_module(packager)


class PackageSkillTests(unittest.TestCase):
    def test_archive_uses_only_committed_skill_files(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            def git(*args):
                return subprocess.check_output(["git", *args], cwd=root, stderr=subprocess.DEVNULL)
            git("init")
            skill = root / "skills/sieve"
            skill.mkdir(parents=True)
            for name in ("SKILL.md", "LICENSE"):
                (skill / name).write_text("committed " + name)
            (root / "private.txt").write_text("outside skill")
            git("add", ".")
            git("-c", "user.name=Test", "-c", "user.email=test@example.invalid",
                "commit", "-m", "fixture")
            (skill / "SKILL.md").write_text("uncommitted changes")
            (skill / "secret.txt").write_text("untracked data")
            first, checksum = packager.package("v1.2.3", root / "one", root)
            second, _ = packager.package("v1.2.3", root / "two", root)
            self.assertEqual(first.read_bytes(), second.read_bytes())
            with zipfile.ZipFile(first) as archive:
                self.assertIsNone(archive.testzip())
                self.assertEqual(archive.namelist(), ["sieve/LICENSE", "sieve/SKILL.md"])
                self.assertEqual(archive.read("sieve/SKILL.md"), b"committed SKILL.md")
            self.assertEqual(checksum.read_text(),
                hashlib.sha256(first.read_bytes()).hexdigest() + "  " + first.name + "\n")

    def test_invalid_version_cannot_escape_output_directory(self):
        for version in ("../escape", "", "tag/name", "-option", "v1\nother"):
            with self.subTest(version=version), self.assertRaises(ValueError):
                packager.package(version, Path("unused"))
