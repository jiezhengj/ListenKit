import subprocess
import tempfile
import unittest
import os
from pathlib import Path
from typing import Optional


REPO_ROOT = Path(__file__).resolve().parents[1]
TRANSCRIBE_SCRIPT = REPO_ROOT / "cli" / "transcribe-audio.sh"


@unittest.skipIf(os.name == "nt", "Bash wrapper compatibility is tested on Unix CI")
class TranscribeAudioTests(unittest.TestCase):
    def write_fake_python(self, path: Path, log_path: Optional[Path] = None) -> None:
        log_line = f"printf '%s\\n' \"$0 $*\" >> {str(log_path)!r}\n" if log_path else ""
        path.write_text(
            "#!/usr/bin/env bash\n"
            f"{log_line}"
            "if [[ \"$1\" == \"-c\" ]]; then\n"
            "  exit 0\n"
            "fi\n"
            "if [[ \"$1\" == \"-m\" && \"$2\" == \"listenkit_cli\" ]]; then\n"
            "  exec \"$LISTENKIT_FASTER_WHISPER_HELPER\"\n"
            "fi\n"
            "exec /bin/sh \"$@\"\n",
            encoding="utf-8",
        )
        path.chmod(0o755)

    def test_default_apple_helper_is_bundled(self) -> None:
        helper = REPO_ROOT / "tools" / "apple-speech-helper" / "run-apple-speech-helper.sh"
        self.assertTrue(helper.is_file())
        self.assertTrue(os.access(helper, os.X_OK))

    def test_rejects_unsupported_engine(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            audio = Path(tmpdir) / "sample.m4a"
            audio.write_bytes(b"fake")
            result = subprocess.run(
                [
                    str(TRANSCRIBE_SCRIPT),
                    "--audio-path",
                    str(audio),
                    "--locale",
                    "ja-JP",
                    "--engine",
                    "whisper",
                ],
                check=False,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("Unsupported engine", result.stderr)

    def test_missing_faster_whisper_environment_without_auto_init_returns_clear_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            audio = Path(tmpdir) / "sample.m4a"
            audio.write_bytes(b"fake")
            env = os.environ.copy()
            env.pop("FASTER_WHISPER_PYTHON", None)
            env.pop("LISTENKIT_AUTO_INIT", None)
            env["LISTENKIT_FASTER_WHISPER_VENV_PYTHON"] = str(Path(tmpdir) / "missing-python")
            result = subprocess.run(
                [
                    str(TRANSCRIBE_SCRIPT),
                    "--audio-path",
                    str(audio),
                    "--locale",
                    "ja-JP",
                ],
                check=False,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("faster-whisper is not initialized", result.stderr)
            self.assertIn("--auto-init", result.stderr)
            self.assertIn("cli/init-faster-whisper.sh", result.stderr)

    def test_default_faster_whisper_helper_can_be_mocked(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            audio = Path(tmpdir) / "sample.m4a"
            helper = Path(tmpdir) / "helper.sh"
            output = Path(tmpdir) / "transcript.json"
            fake_python = Path(tmpdir) / "python"
            audio.write_bytes(b"fake")
            self.write_fake_python(fake_python)
            helper.write_text(
                "#!/usr/bin/env bash\n"
                "printf '{\"engine\":\"faster-whisper\",\"model\":\"small\",\"compute_type\":\"int8\",\"locale\":\"ja-JP\",\"language\":\"ja\",\"full_text\":\"ok\",\"segments\":[],\"timing_complete\":true}\\n'\n",
                encoding="utf-8",
            )
            helper.chmod(0o755)
            env = os.environ.copy()
            env["FASTER_WHISPER_PYTHON"] = str(fake_python)
            env["LISTENKIT_FASTER_WHISPER_HELPER"] = str(helper)
            result = subprocess.run(
                [
                    str(TRANSCRIBE_SCRIPT),
                    "--audio-path",
                    str(audio),
                    "--locale",
                    "ja-JP",
                    "--output",
                    str(output),
                ],
                check=False,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout.strip(), str(output))
            rendered = output.read_text(encoding="utf-8")
            self.assertIn('"engine":"faster-whisper"', rendered)
            self.assertIn('"compute_type":"int8"', rendered)

    def test_explicit_faster_whisper_python_import_times_out(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            audio = Path(tmpdir) / "sample.m4a"
            helper = Path(tmpdir) / "helper.sh"
            fake_python = Path(tmpdir) / "python"
            audio.write_bytes(b"fake")
            fake_python.write_text(
                "#!/usr/bin/env bash\n"
                "if [[ \"$1\" == \"-c\" ]]; then\n"
                "  sleep 3\n"
                "  exit 0\n"
                "fi\n"
                "exec /bin/sh \"$@\"\n",
                encoding="utf-8",
            )
            fake_python.chmod(0o755)
            helper.write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
            helper.chmod(0o755)
            env = os.environ.copy()
            env["FASTER_WHISPER_PYTHON"] = str(fake_python)
            env["LISTENKIT_FASTER_WHISPER_HELPER"] = str(helper)
            env["LISTENKIT_FASTER_WHISPER_IMPORT_TIMEOUT_SECONDS"] = "1"

            result = subprocess.run(
                [
                    str(TRANSCRIBE_SCRIPT),
                    "--audio-path",
                    str(audio),
                    "--locale",
                    "ja-JP",
                ],
                check=False,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env,
                timeout=8,
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("timed out after 1 seconds", result.stderr)

    def test_cached_faster_whisper_model_forces_huggingface_offline(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            audio = Path(tmpdir) / "sample.m4a"
            helper = Path(tmpdir) / "helper.sh"
            output = Path(tmpdir) / "transcript.json"
            fake_python = Path(tmpdir) / "python"
            env_log = Path(tmpdir) / "env.log"
            hf_home = Path(tmpdir) / "hf"
            snapshot = hf_home / "hub" / "models--Systran--faster-whisper-small" / "snapshots" / "abc123"
            snapshot.mkdir(parents=True)
            (snapshot / "model.bin").write_bytes(b"cached")
            audio.write_bytes(b"fake")
            self.write_fake_python(fake_python)
            helper.write_text(
                "#!/usr/bin/env bash\n"
                f"printf 'HF_HUB_OFFLINE=%s\\n' \"${{HF_HUB_OFFLINE:-}}\" > {str(env_log)!r}\n"
                f"printf 'TRANSFORMERS_OFFLINE=%s\\n' \"${{TRANSFORMERS_OFFLINE:-}}\" >> {str(env_log)!r}\n"
                "printf '{\"engine\":\"faster-whisper\",\"model\":\"small\",\"compute_type\":\"int8\",\"locale\":\"ja-JP\",\"language\":\"ja\",\"full_text\":\"ok\",\"segments\":[],\"timing_complete\":true}\\n'\n",
                encoding="utf-8",
            )
            helper.chmod(0o755)
            env = os.environ.copy()
            env.pop("HF_HUB_OFFLINE", None)
            env.pop("TRANSFORMERS_OFFLINE", None)
            env["HF_HOME"] = str(hf_home)
            env["FASTER_WHISPER_PYTHON"] = str(fake_python)
            env["LISTENKIT_FASTER_WHISPER_HELPER"] = str(helper)
            result = subprocess.run(
                [
                    str(TRANSCRIBE_SCRIPT),
                    "--audio-path",
                    str(audio),
                    "--locale",
                    "ja-JP",
                    "--output",
                    str(output),
                ],
                check=False,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            env_text = env_log.read_text(encoding="utf-8")
            self.assertIn("HF_HUB_OFFLINE=1", env_text)
            self.assertIn("TRANSFORMERS_OFFLINE=1", env_text)

    def test_listenkit_runtime_python_is_used_without_env_override(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            audio = Path(tmpdir) / "sample.m4a"
            helper = Path(tmpdir) / "helper.sh"
            output = Path(tmpdir) / "transcript.json"
            fake_python = Path(tmpdir) / "python"
            init_script = Path(tmpdir) / "init.sh"
            audio.write_bytes(b"fake")
            self.write_fake_python(fake_python)
            helper.write_text(
                "#!/usr/bin/env bash\n"
                "printf '{\"engine\":\"faster-whisper\",\"locale\":\"ja-JP\",\"language\":\"ja\",\"full_text\":\"repo venv\",\"segments\":[],\"timing_complete\":true}\\n'\n",
                encoding="utf-8",
            )
            helper.chmod(0o755)
            init_script.write_text("#!/usr/bin/env bash\nexit 99\n", encoding="utf-8")
            init_script.chmod(0o755)
            env = os.environ.copy()
            env.pop("FASTER_WHISPER_PYTHON", None)
            env.pop("LISTENKIT_AUTO_INIT", None)
            env["LISTENKIT_FASTER_WHISPER_VENV_PYTHON"] = str(fake_python)
            env["LISTENKIT_INIT_FASTER_WHISPER"] = str(init_script)
            env["LISTENKIT_FASTER_WHISPER_HELPER"] = str(helper)
            result = subprocess.run(
                [
                    str(TRANSCRIBE_SCRIPT),
                    "--audio-path",
                    str(audio),
                    "--locale",
                    "ja-JP",
                    "--output",
                    str(output),
                ],
                check=False,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn('"full_text":"repo venv"', output.read_text(encoding="utf-8"))

    def test_default_runtime_path_is_local_cache_not_repo_venv(self) -> None:
        script = TRANSCRIBE_SCRIPT.read_text(encoding="utf-8")

        self.assertIn('${HOME}/Library/Caches/ListenKit/venvs/cpython-314', script)
        self.assertNotIn('$repo_root/.venv/bin/python', script)

    def test_auto_init_invokes_init_script_and_continues(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            audio = Path(tmpdir) / "sample.m4a"
            helper = Path(tmpdir) / "helper.sh"
            output = Path(tmpdir) / "transcript.json"
            fake_python = Path(tmpdir) / "python"
            init_script = Path(tmpdir) / "init.sh"
            marker = Path(tmpdir) / "init-called"
            audio.write_bytes(b"fake")
            self.write_fake_python(fake_python)
            helper.write_text(
                "#!/usr/bin/env bash\n"
                "printf '{\"engine\":\"faster-whisper\",\"locale\":\"ja-JP\",\"language\":\"ja\",\"full_text\":\"auto init\",\"segments\":[],\"timing_complete\":true}\\n'\n",
                encoding="utf-8",
            )
            helper.chmod(0o755)
            init_script.write_text(
                "#!/usr/bin/env bash\n"
                f"touch {str(marker)!r}\n"
                f"printf '%s\\n' {str(fake_python)!r}\n",
                encoding="utf-8",
            )
            init_script.chmod(0o755)
            env = os.environ.copy()
            env.pop("FASTER_WHISPER_PYTHON", None)
            env.pop("LISTENKIT_AUTO_INIT", None)
            env["LISTENKIT_FASTER_WHISPER_VENV_PYTHON"] = str(Path(tmpdir) / "missing-python")
            env["LISTENKIT_INIT_FASTER_WHISPER"] = str(init_script)
            env["LISTENKIT_FASTER_WHISPER_HELPER"] = str(helper)
            result = subprocess.run(
                [
                    str(TRANSCRIBE_SCRIPT),
                    "--audio-path",
                    str(audio),
                    "--locale",
                    "ja-JP",
                    "--output",
                    str(output),
                    "--auto-init",
                ],
                check=False,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(marker.exists())
            self.assertIn('"full_text":"auto init"', output.read_text(encoding="utf-8"))

    def test_auto_init_can_be_authorized_by_environment(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            audio = Path(tmpdir) / "sample.m4a"
            helper = Path(tmpdir) / "helper.sh"
            output = Path(tmpdir) / "transcript.json"
            fake_python = Path(tmpdir) / "python"
            init_script = Path(tmpdir) / "init.sh"
            audio.write_bytes(b"fake")
            self.write_fake_python(fake_python)
            helper.write_text(
                "#!/usr/bin/env bash\n"
                "printf '{\"engine\":\"faster-whisper\",\"locale\":\"ja-JP\",\"language\":\"ja\",\"full_text\":\"env init\",\"segments\":[],\"timing_complete\":true}\\n'\n",
                encoding="utf-8",
            )
            helper.chmod(0o755)
            init_script.write_text(
                "#!/usr/bin/env bash\n"
                f"printf '%s\\n' {str(fake_python)!r}\n",
                encoding="utf-8",
            )
            init_script.chmod(0o755)
            env = os.environ.copy()
            env.pop("FASTER_WHISPER_PYTHON", None)
            env["LISTENKIT_AUTO_INIT"] = "1"
            env["LISTENKIT_FASTER_WHISPER_VENV_PYTHON"] = str(Path(tmpdir) / "missing-python")
            env["LISTENKIT_INIT_FASTER_WHISPER"] = str(init_script)
            env["LISTENKIT_FASTER_WHISPER_HELPER"] = str(helper)
            result = subprocess.run(
                [
                    str(TRANSCRIBE_SCRIPT),
                    "--audio-path",
                    str(audio),
                    "--locale",
                    "ja-JP",
                    "--output",
                    str(output),
                ],
                check=False,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn('"full_text":"env init"', output.read_text(encoding="utf-8"))

    def test_faster_whisper_python_override_must_import_package(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            audio = Path(tmpdir) / "sample.m4a"
            fake_python = Path(tmpdir) / "python"
            audio.write_bytes(b"fake")
            fake_python.write_text("#!/usr/bin/env bash\nexit 1\n", encoding="utf-8")
            fake_python.chmod(0o755)
            env = os.environ.copy()
            env["FASTER_WHISPER_PYTHON"] = str(fake_python)
            env["LISTENKIT_FASTER_WHISPER_VENV_PYTHON"] = str(Path(tmpdir) / "missing-python")
            result = subprocess.run(
                [
                    str(TRANSCRIBE_SCRIPT),
                    "--audio-path",
                    str(audio),
                    "--locale",
                    "ja-JP",
                ],
                check=False,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("FASTER_WHISPER_PYTHON cannot import faster_whisper", result.stderr)

    def test_auto_init_failure_stops_transcription(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            audio = Path(tmpdir) / "sample.m4a"
            output = Path(tmpdir) / "transcript.json"
            init_script = Path(tmpdir) / "init.sh"
            audio.write_bytes(b"fake")
            init_script.write_text(
                "#!/usr/bin/env bash\n"
                "echo 'pip failed' >&2\n"
                "exit 42\n",
                encoding="utf-8",
            )
            init_script.chmod(0o755)
            env = os.environ.copy()
            env.pop("FASTER_WHISPER_PYTHON", None)
            env["LISTENKIT_FASTER_WHISPER_VENV_PYTHON"] = str(Path(tmpdir) / "missing-python")
            env["LISTENKIT_INIT_FASTER_WHISPER"] = str(init_script)
            result = subprocess.run(
                [
                    str(TRANSCRIBE_SCRIPT),
                    "--audio-path",
                    str(audio),
                    "--locale",
                    "ja-JP",
                    "--output",
                    str(output),
                    "--auto-init",
                ],
                check=False,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("pip failed", result.stderr)
            self.assertFalse(output.exists())

    def test_apple_helper_can_be_used(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            audio = Path(tmpdir) / "sample.m4a"
            helper = Path(tmpdir) / "helper.sh"
            output = Path(tmpdir) / "transcript.json"
            audio.write_bytes(b"fake")
            helper.write_text(
                "#!/usr/bin/env bash\n"
                "printf '{\"engine\":\"apple\",\"locale\":\"ja-JP\",\"full_text\":\"ok\",\"segments\":[],\"timing_complete\":true}\\n'\n",
                encoding="utf-8",
            )
            helper.chmod(0o755)
            env = os.environ.copy()
            env["APPLE_SPEECH_HELPER"] = str(helper)
            result = subprocess.run(
                [
                    str(TRANSCRIBE_SCRIPT),
                    "--audio-path",
                    str(audio),
                    "--locale",
                    "ja-JP",
                    "--engine",
                    "apple",
                    "--output",
                    str(output),
                ],
                check=False,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout.strip(), str(output))
            self.assertIn('"full_text":"ok"', output.read_text(encoding="utf-8"))

    def test_apple_helper_can_be_used_without_python3_on_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            audio = Path(tmpdir) / "sample.m4a"
            helper = Path(tmpdir) / "helper.sh"
            output = Path(tmpdir) / "transcript.json"
            bin_dir = Path(tmpdir) / "bin"
            bin_dir.mkdir()
            audio.write_bytes(b"fake")
            helper.write_text(
                "#!/usr/bin/env bash\n"
                "printf '{\"engine\":\"apple\",\"locale\":\"ja-JP\",\"full_text\":\"ok\",\"segments\":[],\"timing_complete\":true}\\n'\n",
                encoding="utf-8",
            )
            helper.chmod(0o755)
            for name, target in {
                "awk": "/usr/bin/awk",
                "bash": "/bin/bash",
                "cat": "/bin/cat",
                "dirname": "/usr/bin/dirname",
                "mkdir": "/bin/mkdir",
                "mktemp": "/usr/bin/mktemp",
                "mv": "/bin/mv",
                "rm": "/bin/rm",
            }.items():
                (bin_dir / name).symlink_to(target)

            env = {
                "APPLE_SPEECH_HELPER": str(helper),
                "PATH": str(bin_dir),
            }
            result = subprocess.run(
                [
                    str(TRANSCRIBE_SCRIPT),
                    "--audio-path",
                    str(audio),
                    "--locale",
                    "ja-JP",
                    "--engine",
                    "apple",
                    "--output",
                    str(output),
                ],
                check=False,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout.strip(), str(output))
            self.assertIn('"full_text":"ok"', output.read_text(encoding="utf-8"))

    def test_helper_error_payload_fails_even_with_zero_exit(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            audio = Path(tmpdir) / "sample.m4a"
            helper = Path(tmpdir) / "helper.sh"
            output = Path(tmpdir) / "transcript.json"
            audio.write_bytes(b"fake")
            helper.write_text(
                "#!/usr/bin/env bash\n"
                "printf '{\"error\":{\"type\":\"mock_error\",\"message\":\"failed\"},\"engine\":\"apple\",\"locale\":\"ja-JP\",\"full_text\":\"\",\"segments\":[],\"timing_complete\":false}\\n'\n",
                encoding="utf-8",
            )
            helper.chmod(0o755)
            env = os.environ.copy()
            env["APPLE_SPEECH_HELPER"] = str(helper)
            result = subprocess.run(
                [
                    str(TRANSCRIBE_SCRIPT),
                    "--audio-path",
                    str(audio),
                    "--locale",
                    "ja-JP",
                    "--engine",
                    "apple",
                    "--output",
                    str(output),
                ],
                check=False,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("ASR backend returned error", result.stderr)
            self.assertIn("mock_error", result.stderr)
            self.assertFalse(output.exists())

    def test_pretty_printed_helper_error_payload_fails_even_with_zero_exit(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            audio = Path(tmpdir) / "sample.m4a"
            helper = Path(tmpdir) / "helper.sh"
            output = Path(tmpdir) / "transcript.json"
            audio.write_bytes(b"fake")
            helper.write_text(
                "#!/usr/bin/env bash\n"
                "cat <<'EOF'\n"
                "{\n"
                "  \"error\": {\n"
                "    \"type\": \"mock_error\",\n"
                "    \"message\": \"failed\"\n"
                "  },\n"
                "  \"engine\": \"apple\",\n"
                "  \"locale\": \"ja-JP\",\n"
                "  \"full_text\": \"\",\n"
                "  \"segments\": [],\n"
                "  \"timing_complete\": false\n"
                "}\n"
                "EOF\n",
                encoding="utf-8",
            )
            helper.chmod(0o755)
            env = os.environ.copy()
            env["APPLE_SPEECH_HELPER"] = str(helper)
            result = subprocess.run(
                [
                    str(TRANSCRIBE_SCRIPT),
                    "--audio-path",
                    str(audio),
                    "--locale",
                    "ja-JP",
                    "--engine",
                    "apple",
                    "--output",
                    str(output),
                ],
                check=False,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("ASR backend returned error", result.stderr)
            self.assertIn("mock_error", result.stderr)
            self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
