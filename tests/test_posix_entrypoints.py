import os
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
LISTENKIT_SCRIPT = REPO_ROOT / "cli" / "listenkit.sh"
DOCTOR_SCRIPT = REPO_ROOT / "cli" / "doctor.sh"


@unittest.skipIf(os.name == "nt", "POSIX entrypoints are tested on Unix CI")
class PosixEntrypointTests(unittest.TestCase):
    def poisoned_environment(self) -> dict[str, str]:
        return {
            "HOME": str(Path.home()),
            "PATH": "/usr/bin:/bin:/usr/sbin:/sbin",
            "PYTHONHOME": "/definitely/missing-python-home",
            "PYTHONPATH": "/definitely/missing-python-path",
            "LISTENKIT_CLI_PYTHON": sys.executable,
        }

    def test_unified_entrypoint_runs_with_polluted_agent_python_environment(self) -> None:
        result = subprocess.run(
            [str(LISTENKIT_SCRIPT), "--help"],
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=self.poisoned_environment(),
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("generate-markdown", result.stdout)
        self.assertNotIn("Failed to import encodings", result.stderr)

    def test_doctor_wrapper_uses_unified_entrypoint(self) -> None:
        result = subprocess.run(
            [str(DOCTOR_SCRIPT)],
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=self.poisoned_environment(),
            timeout=20,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("listenkit_version=", result.stdout)
        self.assertIn("platform=", result.stdout)

    def test_cli_python_override_supports_spaces_in_path(self) -> None:
        with tempfile.TemporaryDirectory(prefix="listenkit python path ") as tmp:
            linked_python = Path(tmp) / "python with spaces"
            linked_python.symlink_to(sys.executable)
            environment = self.poisoned_environment()
            environment["LISTENKIT_CLI_PYTHON"] = str(linked_python)
            result = subprocess.run(
                [str(LISTENKIT_SCRIPT), "--help"],
                check=False,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=environment,
            )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_legacy_wrapper_delegates_report_json_to_shared_core(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            report = root / "execution.json"
            result = subprocess.run(
                [
                    str(REPO_ROOT / "cli" / "generate-markdown.sh"),
                    "--input",
                    str(root / "missing.wav"),
                    "--language",
                    "English",
                    "--output",
                    str(root / "out.md"),
                    "--report-json",
                    str(report),
                ],
                check=False,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=self.poisoned_environment(),
            )
            self.assertNotEqual(result.returncode, 0)
            payload = json.loads(report.read_text(encoding="utf-8"))
            self.assertEqual(payload["status"], "error")
            self.assertEqual(payload["command"], "generate-markdown")

    @unittest.skipUnless(sys.platform == "darwin", "Homebrew fallback is macOS-specific")
    def test_non_login_path_adds_existing_homebrew_prefixes(self) -> None:
        expected_prefixes = [
            str(path)
            for path in (Path("/opt/homebrew/bin"), Path("/usr/local/bin"))
            if path.is_dir()
        ]
        if not expected_prefixes:
            self.skipTest("no standard Homebrew prefix exists on this runner")
        result = subprocess.run(
            [
                "/bin/bash",
                "-c",
                "source cli/_common.sh; listenkit_prepare_posix_environment; "
                "printf '%s\\n' \"$PATH\"",
            ],
            cwd=REPO_ROOT,
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=self.poisoned_environment(),
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        actual_path = result.stdout.strip().split(os.pathsep)
        for prefix in expected_prefixes:
            with self.subTest(prefix=prefix):
                self.assertIn(prefix, actual_path)


if __name__ == "__main__":
    unittest.main()
