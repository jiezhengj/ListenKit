import os
import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
INSTALL_SCRIPT = REPO_ROOT / "cli" / "install-agent-instructions.sh"


@unittest.skipIf(os.name == "nt", "Bash wrapper compatibility is tested on Unix CI")
class InstallAgentInstructionsTests(unittest.TestCase):
    def run_script(self, *args: str, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [str(INSTALL_SCRIPT), *args],
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=cwd,
        )

    def test_help_succeeds(self) -> None:
        result = self.run_script("--help")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Usage:", result.stdout)
        self.assertIn("--print", result.stdout)

    def test_target_is_required_unless_print_is_used(self) -> None:
        result = self.run_script()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("--target is required", result.stderr)

    def test_print_outputs_instruction_block_without_writing_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmpdir = Path(tmp)
            result = self.run_script("--print", cwd=tmpdir)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("cli/generate-markdown.sh", result.stdout)
            self.assertIn("Do not call these directly", result.stdout)
            self.assertEqual(list(tmpdir.iterdir()), [])

    def test_print_is_mutually_exclusive_with_target_force_and_dry_run(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            for args in [
                ("--print", "--target", tmp),
                ("--print", "--force"),
                ("--print", "--dry-run"),
            ]:
                result = self.run_script(*args)
                self.assertNotEqual(result.returncode, 0, args)
                self.assertIn("mutually exclusive", result.stderr)

    def test_dry_run_requires_target(self) -> None:
        result = self.run_script("--dry-run")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("--target is required", result.stderr)

    def test_target_directory_installs_named_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target_dir = Path(tmp)
            result = self.run_script("--target", str(target_dir))
            self.assertEqual(result.returncode, 0, result.stderr)
            installed = target_dir / "listenkit-agent-instructions.md"
            self.assertEqual(result.stdout.strip(), str(installed.resolve()))
            self.assertTrue(installed.exists())
            text = installed.read_text(encoding="utf-8")
            self.assertIn("cli/generate-markdown.sh", text)

    def test_target_file_installs_to_file_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "agent-rules.md"
            result = self.run_script("--target", str(target))
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout.strip(), str(target.resolve()))
            self.assertTrue(target.exists())

    def test_existing_file_requires_force(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "agent-rules.md"
            target.write_text("keep me", encoding="utf-8")
            result = self.run_script("--target", str(target))
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("Target already exists", result.stderr)
            self.assertEqual(target.read_text(encoding="utf-8"), "keep me")

    def test_force_overwrites_existing_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "agent-rules.md"
            target.write_text("replace me", encoding="utf-8")
            result = self.run_script("--target", str(target), "--force")
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("cli/generate-markdown.sh", target.read_text(encoding="utf-8"))

    def test_dry_run_does_not_write(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "agent-rules.md"
            result = self.run_script("--target", str(target), "--dry-run")
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("Source:", result.stdout)
            self.assertIn(f"Target: {target.resolve()}", result.stdout)
            self.assertFalse(target.exists())

    def test_missing_parent_directory_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "missing" / "agent-rules.md"
            result = self.run_script("--target", str(target))
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("Target parent directory does not exist", result.stderr)

    def test_runs_from_outside_repo(self) -> None:
        with tempfile.TemporaryDirectory() as cwd, tempfile.TemporaryDirectory() as target_tmp:
            target = Path(target_tmp) / "agent-rules.md"
            result = self.run_script("--target", str(target), cwd=Path(cwd))
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(target.exists())

    def test_installed_content_contains_key_invariants(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "agent-rules.md"
            result = self.run_script("--target", str(target))
            self.assertEqual(result.returncode, 0, result.stderr)
            text = target.read_text(encoding="utf-8")
            for expected in [
                "cli/generate-markdown.sh",
                "--url",
                "--input",
                "--language",
                "--output",
                "--auto-init",
                "Do not call these directly as an integration shortcut",
                "cli/transcribe-audio.sh",
                "tools/*",
            ]:
                self.assertIn(expected, text)


if __name__ == "__main__":
    unittest.main()
