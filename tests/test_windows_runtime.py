import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
INIT_SCRIPT = REPO_ROOT / "cli" / "init-faster-whisper.ps1"
CHECK_SCRIPT = REPO_ROOT / "cli" / "check-runtime.ps1"
GENERATE_SCRIPT = REPO_ROOT / "cli" / "generate-markdown.ps1"
DOCTOR_SCRIPT = REPO_ROOT / "cli" / "doctor.ps1"
LISTENKIT_SCRIPT = REPO_ROOT / "cli" / "listenkit.ps1"
POSIX_LISTENKIT_SCRIPT = REPO_ROOT / "cli" / "listenkit.sh"


def powershell_hosts() -> list[str]:
    if os.name != "nt":
        return []
    return [name for name in ("powershell", "pwsh") if shutil.which(name)]


class WindowsRuntimeTests(unittest.TestCase):
    def test_platform_path_source_declares_local_app_data(self) -> None:
        source = (REPO_ROOT / "listenkit_cli" / "platform_paths.py").read_text(
            encoding="utf-8"
        )
        self.assertIn('env.get("LOCALAPPDATA")', source)
        self.assertIn('"ListenKit" / "venvs" / VENV_NAME', source)

    @unittest.skipUnless(os.name == "nt", "requires Windows")
    def test_all_powershell_hosts_run_public_help(self) -> None:
        hosts = powershell_hosts()
        self.assertTrue(hosts, "No PowerShell host is available")
        for host in hosts:
            with self.subTest(host=host):
                result = subprocess.run(
                    [host, "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(GENERATE_SCRIPT), "--help"],
                    check=False,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    encoding="utf-8",
                    cwd=Path(tempfile.gettempdir()),
                )
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn("--language", result.stdout)
                self.assertIn("--output", result.stdout)

    @unittest.skipUnless(os.name == "nt", "requires Windows")
    def test_dispatcher_sanitizes_polluted_python_environment_before_probe(self) -> None:
        environment = os.environ.copy()
        environment["LISTENKIT_CLI_PYTHON"] = sys.executable
        environment["PYTHONHOME"] = r"C:\definitely-missing-python-home"
        environment["PYTHONPATH"] = r"C:\definitely-missing-python-path"
        for host in powershell_hosts():
            with self.subTest(host=host):
                result = subprocess.run(
                    [
                        host,
                        "-NoProfile",
                        "-ExecutionPolicy",
                        "Bypass",
                        "-File",
                        str(LISTENKIT_SCRIPT),
                        "--help",
                    ],
                    check=False,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    encoding="utf-8",
                    env=environment,
                )
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn("generate-markdown", result.stdout)
                self.assertNotIn("Failed to import encodings", result.stderr)

    @unittest.skipUnless(os.name == "nt", "requires Windows")
    def test_dispatcher_finds_managed_python_with_restricted_path(self) -> None:
        if sys.version_info[:2] < (3, 10):
            self.skipTest("requires venv-capable Python")
        with tempfile.TemporaryDirectory() as tmpdir:
            managed = Path(tmpdir) / "managed runtime with 空格"
            subprocess.run(
                [sys.executable, "-m", "venv", str(managed)],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            for host in powershell_hosts():
                host_path = Path(shutil.which(host) or host)
                environment = os.environ.copy()
                environment.pop("LISTENKIT_CLI_PYTHON", None)
                environment["LISTENKIT_FASTER_WHISPER_VENV_DIR"] = str(managed)
                environment["PYTHONHOME"] = r"C:\definitely-missing-python-home"
                environment["PYTHONPATH"] = r"C:\definitely-missing-python-path"
                environment["PATH"] = str(host_path.parent)
                with self.subTest(host=host):
                    result = subprocess.run(
                        [
                            str(host_path),
                            "-NoProfile",
                            "-ExecutionPolicy",
                            "Bypass",
                            "-File",
                            str(LISTENKIT_SCRIPT),
                            "--help",
                        ],
                        check=False,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True,
                        encoding="utf-8",
                        env=environment,
                    )
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertIn("generate-markdown", result.stdout)

    @unittest.skipUnless(os.name == "nt", "requires Windows")
    def test_direct_module_and_powershell_errors_are_utf8(self) -> None:
        missing = REPO_ROOT / "不存在" / "日本語😀.wav"
        base_environment = os.environ.copy()
        base_environment.pop("PYTHONUTF8", None)
        base_environment.pop("PYTHONIOENCODING", None)
        direct = subprocess.run(
            [
                sys.executable,
                "-m",
                "listenkit_cli",
                "transcribe-audio",
                "--audio-path",
                str(missing),
                "--locale",
                "ja-JP",
            ],
            cwd=REPO_ROOT,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=base_environment,
        )
        self.assertNotEqual(direct.returncode, 0)
        self.assertIn(str(missing), direct.stderr.decode("utf-8", errors="strict"))

        powershell_environment = base_environment.copy()
        powershell_environment["LISTENKIT_CLI_PYTHON"] = sys.executable
        for host in powershell_hosts():
            with self.subTest(host=host):
                result = subprocess.run(
                    [
                        host,
                        "-NoProfile",
                        "-ExecutionPolicy",
                        "Bypass",
                        "-File",
                        str(LISTENKIT_SCRIPT),
                        "transcribe-audio",
                        "--audio-path",
                        str(missing),
                        "--locale",
                        "ja-JP",
                    ],
                    check=False,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    env=powershell_environment,
                )
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(
                    str(missing),
                    result.stderr.decode("utf-8", errors="strict"),
                )

    @unittest.skipUnless(os.name == "nt", "requires Windows")
    def test_git_bash_posix_entrypoint_fails_fast(self) -> None:
        candidates = (
            Path(r"C:\Program Files\Git\bin\bash.exe"),
            Path(r"C:\Program Files\Git\usr\bin\bash.exe"),
        )
        git_bash = next((path for path in candidates if path.is_file()), None)
        if git_bash is None:
            self.skipTest("Git for Windows bash is unavailable")
        result = subprocess.run(
            [str(git_bash), str(POSIX_LISTENKIT_SCRIPT), "--help"],
            cwd=REPO_ROOT,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
        )
        self.assertEqual(result.returncode, 64)
        self.assertIn("not supported", result.stderr)
        self.assertIn("python -m listenkit_cli", result.stderr)
        self.assertIn("listenkit.ps1", result.stderr)

    @unittest.skipUnless(os.name == "nt", "requires Windows")
    def test_all_powershell_hosts_resolve_the_same_default_runtime(self) -> None:
        expected = Path(os.environ["LOCALAPPDATA"]) / "ListenKit" / "venvs" / "cpython-314"
        for host in powershell_hosts():
            with self.subTest(host=host):
                result = subprocess.run(
                    [host, "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(INIT_SCRIPT), "--print-runtime-dir"],
                    check=False,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    encoding="utf-8",
                )
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(Path(result.stdout.strip()), expected)

    @unittest.skipUnless(os.name == "nt", "requires Windows")
    def test_powershell_51_and_7_check_a_realistic_runtime(self) -> None:
        if sys.version_info[:2] != (3, 14):
            self.skipTest("requires Python 3.14")
        with tempfile.TemporaryDirectory() as tmpdir:
            venv_dir = Path(tmpdir) / "runtime with 空格"
            subprocess.run(
                [sys.executable, "-m", "venv", str(venv_dir)],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            venv_python = venv_dir / "Scripts" / "python.exe"
            site_packages = Path(
                subprocess.run(
                    [str(venv_python), "-c", "import site; print(site.getsitepackages()[0])"],
                    check=True,
                    stdout=subprocess.PIPE,
                    text=True,
                    encoding="utf-8",
                    env={**os.environ, "PYTHONUTF8": "1"},
                ).stdout.strip()
            )
            (site_packages / "faster_whisper").mkdir()
            (site_packages / "faster_whisper" / "__init__.py").write_text("", encoding="utf-8")
            dist_info = site_packages / "faster_whisper-1.2.1.dist-info"
            dist_info.mkdir()
            (dist_info / "METADATA").write_text(
                "Metadata-Version: 2.1\nName: faster-whisper\nVersion: 1.2.1\n",
                encoding="utf-8",
            )
            env = os.environ.copy()
            env["LISTENKIT_FASTER_WHISPER_VENV_DIR"] = str(venv_dir)
            env["LISTENKIT_CUDA_AUTO_PREPARE"] = "0"
            for host in powershell_hosts():
                with self.subTest(host=host):
                    initialized = subprocess.run(
                        [host, "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(INIT_SCRIPT)],
                        check=False,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True,
                        encoding="utf-8",
                        env=env,
                    )
                    checked = subprocess.run(
                        [host, "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(CHECK_SCRIPT)],
                        check=False,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True,
                        encoding="utf-8",
                        env=env,
                    )
                    self.assertEqual(initialized.returncode, 0, initialized.stderr)
                    self.assertEqual(Path(initialized.stdout.strip()), venv_python)
                    self.assertEqual(checked.returncode, 0, checked.stderr)
                    self.assertIn("python_version=3.14.", checked.stdout)
                    self.assertIn("faster_whisper_version=1.2.1", checked.stdout)
                    self.assertIn("import_health=ok", checked.stdout)

    @unittest.skipUnless(os.name == "nt", "requires Windows")
    def test_doctor_is_read_only_and_reports_windows_dependencies(self) -> None:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(DOCTOR_SCRIPT)],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("platform=windows", result.stdout)
        self.assertIn("runtime_dir=", result.stdout)
        self.assertIn("yt_dlp_path=", result.stdout)
        self.assertIn("ffmpeg_path=", result.stdout)
        self.assertIn("powershell_version=5.1.", result.stdout)
        self.assertIn("model_small_cache=", result.stdout)

    @unittest.skipUnless(os.name == "nt", "requires Windows")
    def test_native_local_media_workflow_runs_without_bash(self) -> None:
        if sys.version_info[:2] != (3, 14):
            self.skipTest("requires Python 3.14")
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            runtime = root / "runtime with spaces"
            subprocess.run(
                [sys.executable, "-m", "venv", str(runtime)],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            runtime_python = runtime / "Scripts" / "python.exe"
            site_packages = Path(
                subprocess.run(
                    [str(runtime_python), "-c", "import site; print(site.getsitepackages()[0])"],
                    check=True,
                    stdout=subprocess.PIPE,
                    text=True,
                    encoding="utf-8",
                    env={**os.environ, "PYTHONUTF8": "1"},
                ).stdout.strip()
            )
            (site_packages / "faster_whisper").mkdir()
            (site_packages / "faster_whisper" / "__init__.py").write_text("", encoding="utf-8")
            helper = root / "fake transcribe.py"
            helper.write_text(
                "import json\n"
                "print(json.dumps({'schema_version': 1, 'engine': 'faster-whisper', "
                "'locale': 'ja-JP', 'full_text': 'Windows native ok', "
                "'segments': [], 'timing_complete': True}))\n",
                encoding="utf-8",
            )
            bin_dir = root / "fake bin"
            bin_dir.mkdir()
            ffmpeg = bin_dir / "ffmpeg.cmd"
            ffmpeg.write_text(
                "@echo off\r\n"
                "setlocal\r\n"
                "set \"last=\"\r\n"
                ":loop\r\n"
                "if \"%~1\"==\"\" goto done\r\n"
                "set \"last=%~1\"\r\n"
                "shift\r\n"
                "goto loop\r\n"
                ":done\r\n"
                "copy /Y \"%LISTENKIT_TEST_SOURCE%\" \"%last%\" >nul\r\n",
                encoding="utf-8",
            )
            source = root / "输入 media.wav"
            source.write_bytes(b"synthetic media")
            env = os.environ.copy()
            env["PATH"] = str(bin_dir) + os.pathsep + env["PATH"]
            env["LISTENKIT_FASTER_WHISPER_VENV_DIR"] = str(runtime)
            env["LISTENKIT_FASTER_WHISPER_HELPER"] = str(helper)
            env["LISTENKIT_TEST_SOURCE"] = str(source)
            for host in powershell_hosts():
                output = root / f"output {host}" / "结果.md"
                with self.subTest(host=host):
                    result = subprocess.run(
                        [
                            host,
                            "-NoProfile",
                            "-ExecutionPolicy",
                            "Bypass",
                            "-File",
                            str(GENERATE_SCRIPT),
                            "--input",
                            str(source),
                            "--language",
                            "Japanese",
                            "--output",
                            str(output),
                        ],
                        check=False,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True,
                        encoding="utf-8",
                        env=env,
                    )
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertTrue(output.is_file())
                    self.assertTrue(output.with_suffix(".json").is_file())
                    self.assertIn("Windows native ok", output.read_text(encoding="utf-8"))

    @unittest.skipUnless(os.name == "nt", "requires Windows")
    def test_native_url_workflow_prefers_subtitles_and_imports_audio(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            bin_dir = root / "fake tools"
            bin_dir.mkdir()
            helper = root / "fake_ytdlp.py"
            helper.write_text(
                "import pathlib, sys\n"
                "args = sys.argv[1:]\n"
                "if '--skip-download' in args and '--print' in args and 'title' in args:\n"
                "    print('Mock Windows 标题')\n"
                "elif '--write-subs' in args:\n"
                "    root = pathlib.Path(args[args.index('--paths') + 1])\n"
                "    (root / 'subtitle.ja.vtt').write_text("
                "'WEBVTT\\n\\n00:00.000 --> 00:01.000\\n字幕 workflow ok\\n', encoding='utf-8')\n"
                "elif '--write-auto-subs' in args:\n"
                "    raise SystemExit(1)\n"
                "elif '--extract-audio' in args:\n"
                "    root = pathlib.Path(args[args.index('--paths') + 1])\n"
                "    template = args[args.index('--output') + 1]\n"
                "    audio_format = args[args.index('--audio-format') + 1]\n"
                "    name = template.replace('%(ext)s', audio_format)\n"
                "    output = root / name\n"
                "    output.parent.mkdir(parents=True, exist_ok=True)\n"
                "    output.write_bytes(b'audio')\n"
                "    print(output)\n"
                "else:\n"
                "    raise SystemExit(2)\n",
                encoding="utf-8",
            )
            (bin_dir / "yt-dlp.cmd").write_text(
                '@"%LISTENKIT_TEST_PYTHON%" "%LISTENKIT_TEST_YTDLP_HELPER%" %*\r\n',
                encoding="utf-8",
            )
            (bin_dir / "ffmpeg.cmd").write_text("@exit /b 0\r\n", encoding="utf-8")
            env = os.environ.copy()
            env["PATH"] = str(bin_dir) + os.pathsep + env["PATH"]
            env["LISTENKIT_TEST_PYTHON"] = sys.executable
            env["LISTENKIT_TEST_YTDLP_HELPER"] = str(helper)
            for host in powershell_hosts():
                output = root / f"url output {host}" / "note.md"
                with self.subTest(host=host):
                    result = subprocess.run(
                        [
                            host,
                            "-NoProfile",
                            "-ExecutionPolicy",
                            "Bypass",
                            "-File",
                            str(GENERATE_SCRIPT),
                            "--url",
                            "https://example.test/video",
                            "--language",
                            "Japanese",
                            "--output",
                            str(output),
                        ],
                        check=False,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True,
                        encoding="utf-8",
                        env=env,
                    )
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertTrue(output.is_file())
                    self.assertTrue((output.parent / "audio" / "note.m4a").is_file())
                    rendered = output.read_text(encoding="utf-8")
                    self.assertIn("# Mock Windows 标题", rendered)
                    self.assertIn("字幕 workflow ok", rendered)
                    payload = json.loads(output.with_suffix(".json").read_text(encoding="utf-8"))
                    self.assertEqual(payload["engine"], "yt-dlp-subtitles")


if __name__ == "__main__":
    unittest.main()
