import os
import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
INIT_SCRIPT = REPO_ROOT / "cli" / "init-faster-whisper.sh"
CHECK_RUNTIME = REPO_ROOT / "cli" / "check-runtime.sh"
COMMON_SCRIPT = REPO_ROOT / "cli" / "_common.sh"
REQUIREMENTS = REPO_ROOT / "requirements-faster-whisper.txt"
CUDA_REQUIREMENTS = REPO_ROOT / "requirements-faster-whisper-cuda.txt"
MLX_REQUIREMENTS = REPO_ROOT / "requirements-mlx-whisper.txt"
PYTHON314 = Path("/opt/homebrew/bin/python3.14")


@unittest.skipIf(os.name == "nt", "Bash wrapper compatibility is tested on Unix CI")
class InitFasterWhisperTests(unittest.TestCase):
    def test_requirements_pin_only_direct_faster_whisper_dependency(self) -> None:
        requirements = [
            line.strip()
            for line in REQUIREMENTS.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        ]

        self.assertEqual(requirements, ["faster-whisper==1.2.1"])

    def test_init_installs_from_requirements_file(self) -> None:
        script = INIT_SCRIPT.read_text(encoding="utf-8")

        self.assertIn("requirements-faster-whisper.txt", script)
        self.assertIn('-r "$requirements_file"', script)
        self.assertNotIn("pip install faster-whisper", script)

    def test_managed_cuda_requirements_pin_supported_major_versions(self) -> None:
        requirements = [
            line.strip()
            for line in CUDA_REQUIREMENTS.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        ]

        self.assertEqual(
            requirements,
            ["nvidia-cublas-cu12>=12.4,<13", "nvidia-cudnn-cu12>=9,<10"],
        )
        script = INIT_SCRIPT.read_text(encoding="utf-8")
        self.assertIn("prepare_runtime_acceleration", script)

    def test_managed_mlx_requirements_pin_verified_version(self) -> None:
        requirements = [
            line.strip()
            for line in MLX_REQUIREMENTS.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        ]

        self.assertEqual(requirements, ["mlx-whisper==0.4.3"])

    def test_default_runtime_is_local_cache_not_repo_venv(self) -> None:
        init_script = INIT_SCRIPT.read_text(encoding="utf-8")
        check_script = CHECK_RUNTIME.read_text(encoding="utf-8")

        expected = '${HOME}/Library/Caches/ListenKit/venvs/cpython-314'
        self.assertIn(expected, init_script)
        self.assertIn(expected, check_script)
        self.assertNotIn('$repo_root/.venv/bin/python', init_script)
        self.assertNotIn('$repo_root/.venv/bin/python', check_script)

    def test_existing_python314_venv_is_supported(self) -> None:
        if not PYTHON314.is_file():
            self.skipTest("Homebrew Python 3.14 is not installed")
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            repo = root / "ListenKit"
            script = repo / "cli" / "init-faster-whisper.sh"
            venv_dir = root / "runtime"
            venv_python = venv_dir / "bin" / "python"
            script.parent.mkdir(parents=True)
            venv_python.parent.mkdir(parents=True)
            script.write_text(INIT_SCRIPT.read_text(encoding="utf-8"), encoding="utf-8")
            (script.parent / "_common.sh").write_text(
                COMMON_SCRIPT.read_text(encoding="utf-8"), encoding="utf-8"
            )
            script.chmod(0o755)
            venv_python.write_text(
                "#!/usr/bin/env bash\n"
                "if [[ \"$1\" == \"-\" || \"$1\" == \"-c\" ]]; then exit 0; fi\n"
                "exit 1\n",
                encoding="utf-8",
            )
            venv_python.chmod(0o755)
            env = os.environ.copy()
            env["LISTENKIT_FASTER_WHISPER_VENV_DIR"] = str(venv_dir)

            result = subprocess.run(
                [str(script)],
                check=False,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout.strip(), str(venv_python))

    def test_import_health_check_times_out(self) -> None:
        if not PYTHON314.is_file():
            self.skipTest("Homebrew Python 3.14 is not installed")
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            repo = root / "ListenKit"
            script = repo / "cli" / "init-faster-whisper.sh"
            venv_dir = root / "runtime"
            venv_python = venv_dir / "bin" / "python"
            script.parent.mkdir(parents=True)
            venv_python.parent.mkdir(parents=True)
            script.write_text(INIT_SCRIPT.read_text(encoding="utf-8"), encoding="utf-8")
            (script.parent / "_common.sh").write_text(
                COMMON_SCRIPT.read_text(encoding="utf-8"), encoding="utf-8"
            )
            script.chmod(0o755)
            venv_python.write_text(
                "#!/usr/bin/env bash\n"
                "if [[ \"$1\" == \"-\" ]]; then exit 0; fi\n"
                "if [[ \"$1\" == \"-c\" && \"$2\" == *importlib.metadata* ]]; then exit 0; fi\n"
                "if [[ \"$1\" == \"-c\" ]]; then sleep 3; exit 0; fi\n"
                "exit 1\n",
                encoding="utf-8",
            )
            venv_python.chmod(0o755)
            env = os.environ.copy()
            env["LISTENKIT_FASTER_WHISPER_VENV_DIR"] = str(venv_dir)
            env["LISTENKIT_FASTER_WHISPER_IMPORT_TIMEOUT_SECONDS"] = "1"

            result = subprocess.run(
                [str(script)],
                check=False,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env,
                timeout=8,
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("timed out after 1 seconds", result.stderr)

    def test_init_refuses_icloud_runtime_target(self) -> None:
        env = os.environ.copy()
        env["LISTENKIT_FASTER_WHISPER_VENV_DIR"] = "/Users/test/Library/Mobile Documents/ListenKit/.venv"

        result = subprocess.run(
            [str(INIT_SCRIPT)],
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("iCloud-backed", result.stderr)


if __name__ == "__main__":
    unittest.main()
