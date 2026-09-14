import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from listenkit_cli.clean import clean_workspace

REPO_ROOT = Path(__file__).resolve().parents[1]
CLEAN_SCRIPT = REPO_ROOT / "cli" / "clean.sh"


class CleanTests(unittest.TestCase):
    def test_clean_workspace_dry_run_does_not_delete(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            pycache = root / "pkg" / "__pycache__"
            pycache.mkdir(parents=True)
            (pycache / "mod.cpython-314.pyc").write_bytes(b"dummy")

            source_file = root / "pkg" / "mod.py"
            source_file.write_text("print('hello')", encoding="utf-8")

            pytest_cache = root / ".pytest_cache"
            pytest_cache.mkdir()

            result = clean_workspace(root, dry_run=True)
            self.assertTrue(result.dry_run)
            self.assertGreaterEqual(result.removed_dirs, 2)
            self.assertTrue(pycache.exists())
            self.assertTrue(source_file.exists())
            self.assertTrue(pytest_cache.exists())

    def test_clean_workspace_removes_caches_and_preserves_work_and_source(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            pycache = root / "pkg" / "__pycache__"
            pycache.mkdir(parents=True)
            (pycache / "mod.cpython-314.pyc").write_bytes(b"dummy")

            loose_pyc = root / "pkg" / "old.pyc"
            loose_pyc.write_bytes(b"dummy")

            ds_store = root / "pkg" / ".DS_Store"
            ds_store.write_bytes(b"dummy")

            sync_conflict = root / "pkg" / "file.sync-conflict-20260914.py"
            sync_conflict.write_text("conflict", encoding="utf-8")

            pytest_cache = root / ".pytest_cache"
            pytest_cache.mkdir()

            helper_build = root / "tools" / "apple-speech-helper" / ".build"
            helper_build.mkdir(parents=True)
            (helper_build / "helper.app").mkdir()

            source_file = root / "pkg" / "mod.py"
            source_file.write_text("print('hello')", encoding="utf-8")

            work_file = root / "work" / "transcript.md"
            work_file.parent.mkdir(parents=True)
            work_file.write_text("user note", encoding="utf-8")

            result = clean_workspace(root, dry_run=False)
            self.assertFalse(result.dry_run)
            self.assertFalse(pycache.exists())
            self.assertFalse(loose_pyc.exists())
            self.assertFalse(ds_store.exists())
            self.assertFalse(sync_conflict.exists())
            self.assertFalse(pytest_cache.exists())
            self.assertFalse(helper_build.exists())

            # Preserved files
            self.assertTrue(source_file.exists())
            self.assertTrue(work_file.exists())

    def test_clean_workspace_cleans_runtime_when_requested(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            mock_runtime = root / "mock_venv"
            mock_runtime.mkdir()
            (mock_runtime / "bin").mkdir()
            (mock_runtime / "bin" / "python").write_text("#!/bin/sh", encoding="utf-8")

            env = {"LISTENKIT_FASTER_WHISPER_VENV_DIR": str(mock_runtime)}
            result = clean_workspace(root, clean_runtime=True, environment=env)
            self.assertFalse(mock_runtime.exists())
            self.assertIn(str(mock_runtime), result.targets)

    @unittest.skipIf(os.name == "nt", "POSIX clean.sh tested on Unix")
    def test_clean_script_dry_run(self) -> None:
        result = subprocess.run(
            [str(CLEAN_SCRIPT), "--dry-run"],
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("ListenKit:", result.stdout)


if __name__ == "__main__":
    unittest.main()
