import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
CHECK_RUNTIME = REPO_ROOT / "cli" / "check-runtime.sh"
DEFAULT_RUNTIME_PYTHON = Path.home() / "Library/Caches/ListenKit/venvs/cpython-314/bin/python"
FASTER_WHISPER_HELPER = REPO_ROOT / "tools" / "faster-whisper" / "transcribe.py"
MLX_WHISPER_HELPER = REPO_ROOT / "tools" / "mlx-whisper" / "transcribe.py"
APPLE_HELPER_SOURCE = REPO_ROOT / "tools" / "apple-speech-helper" / "SpeechPermissionApp" / "main.swift"


@unittest.skipIf(os.name == "nt", "Bash runtime contract is tested on Unix CI")
class RuntimeContractTests(unittest.TestCase):
    @unittest.skipUnless(DEFAULT_RUNTIME_PYTHON.is_file(), "requires initialized default runtime")
    def test_runtime_check_reports_python_and_faster_whisper_versions(self) -> None:
        result = subprocess.run(
            [str(CHECK_RUNTIME)],
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("python_version=3.14.", result.stdout)
        self.assertIn("faster_whisper_version=1.2.1", result.stdout)

    @unittest.skipUnless(DEFAULT_RUNTIME_PYTHON.is_file(), "requires initialized default runtime")
    def test_faster_whisper_error_payload_has_schema_version(self) -> None:
        result = subprocess.run(
            [str(DEFAULT_RUNTIME_PYTHON), str(FASTER_WHISPER_HELPER), "/missing/audio.mp3"],
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(json.loads(result.stdout)["schema_version"], 1)

    def test_runtime_check_rejects_unpinned_faster_whisper_version(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            fake_python = Path(tmpdir) / "python"
            fake_python.write_text(
                "#!/usr/bin/env bash\n"
                "if [[ \"$1\" == \"-\" ]]; then\n"
                "  printf 'python_executable=%s\\npython_version=3.14.3\\nabi_tag=cpython-314\\nfaster_whisper_version=9.9.9\\n' \"$0\"\n"
                "  exit 0\n"
                "fi\n"
                "if [[ \"$1\" == \"-c\" ]]; then exit 0; fi\n"
                "exit 1\n",
                encoding="utf-8",
            )
            os.chmod(fake_python, 0o755)

            result = subprocess.run(
                [str(CHECK_RUNTIME), "--python", str(fake_python)],
                check=False,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("requires faster-whisper 1.2.1", result.stderr)

    def test_runtime_check_rejects_icloud_runtime(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            fake_python = Path(tmpdir) / "python"
            fake_python.write_text(
                "#!/usr/bin/env bash\n"
                "if [[ \"$1\" == \"-\" ]]; then\n"
                "  printf 'python_executable=%s\\npython_version=3.14.3\\nabi_tag=cpython-314\\nruntime_prefix=/Users/test/Library/Mobile Documents/ListenKit/.venv\\nfaster_whisper_version=1.2.1\\n' \"$0\"\n"
                "  exit 0\n"
                "fi\n"
                "if [[ \"$1\" == \"-c\" ]]; then exit 0; fi\n"
                "exit 1\n",
                encoding="utf-8",
            )
            os.chmod(fake_python, 0o755)

            result = subprocess.run(
                [str(CHECK_RUNTIME), "--python", str(fake_python)],
                check=False,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("iCloud-backed", result.stderr)

    def test_apple_helper_declares_schema_version(self) -> None:
        source = APPLE_HELPER_SOURCE.read_text(encoding="utf-8")

        self.assertIn("let schemaVersion: Int", source)
        self.assertIn('case schemaVersion = "schema_version"', source)


class FasterWhisperHelperContractTests(unittest.TestCase):
    def test_helper_forwards_device_and_emits_device_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            package = root / "faster_whisper"
            package.mkdir()
            (package / "__init__.py").write_text(
                "class Segment:\n"
                "    start = 0.0\n"
                "    end = 1.0\n"
                "    text = 'ok'\n"
                "class Info:\n"
                "    language = 'en'\n"
                "    language_probability = 1.0\n"
                "class WhisperModel:\n"
                "    def __init__(self, model, **kwargs):\n"
                "        assert kwargs == {'device': 'cuda', 'device_index': 2, 'compute_type': 'float16'}\n"
                "    def transcribe(self, *args, **kwargs):\n"
                "        return iter([Segment()]), Info()\n",
                encoding="utf-8",
            )
            audio = root / "输入 audio.wav"
            audio.write_bytes(b"audio")
            env = os.environ.copy()
            env["PYTHONPATH"] = str(root)
            env["PYTHONUTF8"] = "1"
            result = subprocess.run(
                [
                    sys.executable,
                    str(FASTER_WHISPER_HELPER),
                    str(audio),
                    "--locale",
                    "en-US",
                    "--device",
                    "cuda",
                    "--device-index",
                    "2",
                    "--compute-type",
                    "float16",
                ],
                env=env,
                check=False,
                text=True,
                encoding="utf-8",
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["device"], "cuda")
            self.assertEqual(payload["device_index"], 2)
            self.assertEqual(payload["compute_type"], "float16")


class MlxWhisperHelperContractTests(unittest.TestCase):
    def test_helper_requires_metal_and_normalizes_segments(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            mlx_package = root / "mlx"
            mlx_package.mkdir()
            (mlx_package / "__init__.py").write_text("", encoding="utf-8")
            (mlx_package / "core.py").write_text(
                "class Metal:\n"
                "    @staticmethod\n"
                "    def is_available(): return True\n"
                "metal = Metal()\n",
                encoding="utf-8",
            )
            (root / "mlx_whisper.py").write_text(
                "def transcribe(audio, **kwargs):\n"
                "    assert kwargs['path_or_hf_repo'] == 'test/model'\n"
                "    assert kwargs['language'] == 'zh'\n"
                "    return {'text': 'Metal 正常', 'language': 'zh', "
                "'segments': [{'start': 0, 'end': 1.25, 'text': ' Metal 正常 '}]}\n",
                encoding="utf-8",
            )
            audio = root / "输入 audio.wav"
            audio.write_bytes(b"audio")
            env = {**os.environ, "PYTHONPATH": str(root), "PYTHONUTF8": "1"}
            result = subprocess.run(
                [
                    sys.executable,
                    str(MLX_WHISPER_HELPER),
                    str(audio),
                    "--locale",
                    "zh-CN",
                    "--model",
                    "test/model",
                ],
                env=env,
                check=False,
                text=True,
                encoding="utf-8",
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["engine"], "mlx-whisper")
            self.assertEqual(payload["device"], "metal")
            self.assertEqual(payload["compute_type"], "float16")
            self.assertEqual(payload["segments"][0]["text"], "Metal 正常")


if __name__ == "__main__":
    unittest.main()
