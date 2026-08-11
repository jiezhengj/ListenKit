import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Optional


REPO_ROOT = Path(__file__).resolve().parents[1]
GENERATE_SCRIPT = REPO_ROOT / "cli" / "generate-markdown.sh"


@unittest.skipIf(os.name == "nt", "Bash wrapper compatibility is tested on Unix CI")
class GenerateMarkdownTests(unittest.TestCase):
    def write_fake_python(self, path: Path) -> None:
        path.write_text(
            "#!/usr/bin/env bash\n"
            "if [[ \"$1\" == \"-c\" ]]; then\n"
            "  exit 0\n"
            "fi\n"
            "if [[ \"$1\" == \"-m\" && \"$2\" == \"listenkit_cli\" ]]; then\n"
            "  exec \"$LISTENKIT_TEST_PYTHON\" \"$@\"\n"
            "fi\n"
            "exec /bin/sh \"$@\"\n",
            encoding="utf-8",
        )
        path.chmod(0o755)

    def write_fake_transcribe_helper(self, path: Path, text: str, log_path: Optional[Path] = None) -> None:
        log_line = f"printf '%s\\n' \"$@\" > {str(log_path)!r}\n" if log_path else ""
        path.write_text(
            "#!/usr/bin/env bash\n"
            f"{log_line}"
            f"printf '{{\"engine\":\"faster-whisper\",\"locale\":\"%s\",\"language\":\"ja\",\"full_text\":\"{text}\",\"segments\":[],\"timing_complete\":true}}\\n' \"$3\"\n",
            encoding="utf-8",
        )
        path.chmod(0o755)

    def base_env(self, tmpdir: Path) -> dict[str, str]:
        fake_python = tmpdir / "python"
        helper = tmpdir / "transcribe-helper.sh"
        self.write_fake_python(fake_python)
        self.write_fake_transcribe_helper(helper, "generated transcript", tmpdir / "transcribe.log")
        env = os.environ.copy()
        env["FASTER_WHISPER_PYTHON"] = str(fake_python)
        env["LISTENKIT_FASTER_WHISPER_HELPER"] = str(helper)
        env["LISTENKIT_TEST_PYTHON"] = sys.executable
        return env

    def add_fake_url_tools(self, tmpdir: Path, env: dict[str, str], imported: Path) -> None:
        bin_dir = tmpdir / "bin"
        bin_dir.mkdir(exist_ok=True)
        (bin_dir / "ffmpeg").write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
        (bin_dir / "yt-dlp").write_text(
            "#!/usr/bin/env bash\n"
            "prev=\"\"\n"
            "for arg in \"$@\"; do\n"
            "  if [[ \"$prev\" == \"--print\" && \"$arg\" == \"title\" ]]; then\n"
            "    printf 'Original Video Title\\n'\n"
            "    exit 0\n"
            "  fi\n"
            "  prev=\"$arg\"\n"
            "done\n"
            "printf '%s\\n' \"$@\" > \"$YTDLP_LOG\"\n"
            "mkdir -p \"$(dirname \"$YTDLP_OUTPUT\")\"\n"
            "touch \"$YTDLP_OUTPUT\"\n"
            "printf '%s\\n' \"$YTDLP_OUTPUT\"\n",
            encoding="utf-8",
        )
        os.chmod(bin_dir / "ffmpeg", 0o755)
        os.chmod(bin_dir / "yt-dlp", 0o755)
        env["PATH"] = f"{bin_dir}:{env['PATH']}"
        env["YTDLP_LOG"] = str(tmpdir / "yt-dlp.log")
        env["YTDLP_OUTPUT"] = str(imported)

    def add_fake_url_tools_with_subtitles(self, tmpdir: Path, env: dict[str, str], imported: Path) -> None:
        bin_dir = tmpdir / "bin"
        bin_dir.mkdir(exist_ok=True)
        (bin_dir / "ffmpeg").write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
        (bin_dir / "yt-dlp").write_text(
            """#!/usr/bin/env bash
mode="audio"
paths=""
prev=""
for arg in "$@"; do
  if [[ "$prev" == "--print" && "$arg" == "title" ]]; then
    printf 'Original Video Title\n'
    exit 0
  fi
  if [[ "$arg" == "--skip-download" ]]; then mode="subtitles"; fi
  if [[ "$prev" == "--paths" ]]; then paths="$arg"; fi
  prev="$arg"
done
if [[ "$mode" == "subtitles" ]]; then
  mkdir -p "$paths"
  cat > "$paths/subtitle.ja.vtt" <<'VTT'
WEBVTT

00:00:01.000 --> 00:00:02.000
字幕テキスト
VTT
  exit 0
fi
printf '%s\n' "$@" > "$YTDLP_LOG"
mkdir -p "$(dirname "$YTDLP_OUTPUT")"
touch "$YTDLP_OUTPUT"
printf '%s\n' "$YTDLP_OUTPUT"
""",
            encoding="utf-8",
        )
        os.chmod(bin_dir / "ffmpeg", 0o755)
        os.chmod(bin_dir / "yt-dlp", 0o755)
        env["PATH"] = f"{bin_dir}:{env['PATH']}"
        env["YTDLP_LOG"] = str(tmpdir / "yt-dlp.log")
        env["YTDLP_OUTPUT"] = str(imported)

    def add_fake_url_tools_with_subtitles_and_audio_failure(self, tmpdir: Path, env: dict[str, str]) -> None:
        bin_dir = tmpdir / "bin"
        bin_dir.mkdir(exist_ok=True)
        (bin_dir / "ffmpeg").write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
        (bin_dir / "yt-dlp").write_text(
            """#!/usr/bin/env bash
mode="audio"
paths=""
prev=""
for arg in "$@"; do
  if [[ "$prev" == "--print" && "$arg" == "title" ]]; then
    printf 'Original Video Title\n'
    exit 0
  fi
  if [[ "$arg" == "--skip-download" ]]; then mode="subtitles"; fi
  if [[ "$prev" == "--paths" ]]; then paths="$arg"; fi
  prev="$arg"
done
if [[ "$mode" == "subtitles" ]]; then
  mkdir -p "$paths"
  cat > "$paths/subtitle.ja.vtt" <<'VTT'
WEBVTT

00:00:01.000 --> 00:00:02.000
字幕だけ成功
VTT
  exit 0
fi
echo 'mock audio import failure' >&2
exit 42
""",
            encoding="utf-8",
        )
        os.chmod(bin_dir / "ffmpeg", 0o755)
        os.chmod(bin_dir / "yt-dlp", 0o755)
        env["PATH"] = f"{bin_dir}:{env['PATH']}"

    def add_fake_ffmpeg(self, tmpdir: Path, env: dict[str, str]) -> None:
        bin_dir = tmpdir / "bin"
        bin_dir.mkdir(exist_ok=True)
        (bin_dir / "ffmpeg").write_text(
            "#!/usr/bin/env bash\n"
            "printf '%s\\n' \"$@\" > \"$FFMPEG_LOG\"\n"
            "out=\"${@: -1}\"\n"
            "mkdir -p \"$(dirname \"$out\")\"\n"
            "touch \"$out\"\n",
            encoding="utf-8",
        )
        os.chmod(bin_dir / "ffmpeg", 0o755)
        env["PATH"] = f"{bin_dir}:{env['PATH']}"
        env["FFMPEG_LOG"] = str(tmpdir / "ffmpeg.log")

    def test_help_groups_public_parameters(self) -> None:
        result = subprocess.run(
            [str(GENERATE_SCRIPT), "--help"],
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        for heading in [
            "Core:",
            "Optional overrides:",
            "ASR options:",
            "Import options:",
            "URL-only advanced options:",
            "Other:",
        ]:
            self.assertIn(heading, result.stdout)

    def test_url_input_derives_locale_title_and_renders_markdown(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmpdir = Path(tmp)
            output = tmpdir / "out" / "sample.md"
            imported = tmpdir / "out" / "audio" / "sample.m4a"
            env = self.base_env(tmpdir)
            self.add_fake_url_tools(tmpdir, env, imported)

            result = subprocess.run(
                [
                    str(GENERATE_SCRIPT),
                    "--url",
                    "https://example.com/video",
                    "--language",
                    "Japanese",
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
            self.assertIn("# Original Video Title", rendered)
            self.assertIn("- Source: <https://example.com/video>", rendered)
            self.assertIn("Locale: `ja-JP`", rendered)
            self.assertIn("generated transcript", rendered)
            self.assertTrue((tmpdir / "out" / "sample.json").exists())

    def test_url_title_override_wins_over_video_title(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmpdir = Path(tmp)
            output = tmpdir / "out" / "sample.md"
            imported = tmpdir / "out" / "audio" / "sample.m4a"
            env = self.base_env(tmpdir)
            self.add_fake_url_tools(tmpdir, env, imported)

            result = subprocess.run(
                [
                    str(GENERATE_SCRIPT),
                    "--url",
                    "https://example.com/video",
                    "--language",
                    "Japanese",
                    "--title",
                    "Manual URL Title",
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
            rendered = output.read_text(encoding="utf-8")
            self.assertIn("# Manual URL Title", rendered)
            self.assertNotIn("# Original Video Title", rendered)

    def test_url_subtitles_skip_asr_but_still_import_audio(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmpdir = Path(tmp)
            output = tmpdir / "out" / "sample.md"
            imported = tmpdir / "out" / "audio" / "sample.m4a"
            env = self.base_env(tmpdir)
            self.add_fake_url_tools_with_subtitles(tmpdir, env, imported)

            result = subprocess.run(
                [
                    str(GENERATE_SCRIPT),
                    "--url",
                    "https://example.com/video",
                    "--language",
                    "Japanese",
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
            rendered = output.read_text(encoding="utf-8")
            self.assertIn("# Original Video Title", rendered)
            self.assertIn("字幕テキスト", rendered)
            self.assertNotIn("generated transcript", rendered)
            self.assertTrue(imported.exists())
            self.assertFalse((tmpdir / "transcribe.log").exists())

    def test_url_subtitles_allow_markdown_when_audio_import_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmpdir = Path(tmp)
            output = tmpdir / "out" / "sample.md"
            env = self.base_env(tmpdir)
            self.add_fake_url_tools_with_subtitles_and_audio_failure(tmpdir, env)

            result = subprocess.run(
                [
                    str(GENERATE_SCRIPT),
                    "--url",
                    "https://example.com/video",
                    "--language",
                    "Japanese",
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
            self.assertIn("mock audio import failure", result.stderr)
            self.assertIn("Audio import failed after subtitles were extracted", result.stderr)
            self.assertIn("no local listening audio was created", result.stderr)
            self.assertIn("Audio Hijack", result.stderr)
            rendered = output.read_text(encoding="utf-8")
            self.assertIn("# Original Video Title", rendered)
            self.assertIn("字幕だけ成功", rendered)
            self.assertFalse((tmpdir / "transcribe.log").exists())

    def test_local_input_derives_title_from_input_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmpdir = Path(tmp)
            source = tmpdir / "recording.wav"
            output = tmpdir / "out" / "ignored-output-name.md"
            source.write_bytes(b"fake")
            env = self.base_env(tmpdir)
            self.add_fake_ffmpeg(tmpdir, env)

            result = subprocess.run(
                [
                    str(GENERATE_SCRIPT),
                    "--input",
                    str(source),
                    "--language",
                    "English",
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
            rendered = output.read_text(encoding="utf-8")
            self.assertIn("# recording", rendered)
            self.assertIn(f"- Source: `{source}`", rendered)
            self.assertIn("Locale: `en-US`", rendered)

    def test_language_mapping_supports_chinese_and_korean(self) -> None:
        cases = [
            ("中文", "zh-CN"),
            ("한국어", "ko-KR"),
        ]
        for language, expected_locale in cases:
            with self.subTest(language=language):
                with tempfile.TemporaryDirectory() as tmp:
                    tmpdir = Path(tmp)
                    source = tmpdir / "clip.wav"
                    output = tmpdir / "out.md"
                    source.write_bytes(b"fake")
                    env = self.base_env(tmpdir)
                    self.add_fake_ffmpeg(tmpdir, env)
                    result = subprocess.run(
                        [
                            str(GENERATE_SCRIPT),
                            "--input",
                            str(source),
                            "--language",
                            language,
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
                    self.assertIn(f"Locale: `{expected_locale}`", output.read_text(encoding="utf-8"))

    def test_unknown_language_requires_locale_override(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmpdir = Path(tmp)
            source = tmpdir / "clip.wav"
            source.write_bytes(b"fake")
            result = subprocess.run(
                [
                    str(GENERATE_SCRIPT),
                    "--input",
                    str(source),
                    "--language",
                    "Klingon",
                    "--output",
                    str(tmpdir / "out.md"),
                ],
                check=False,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("Cannot derive ASR locale", result.stderr)
            self.assertIn("--locale", result.stderr)

    def test_locale_override_and_title_override_are_used(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmpdir = Path(tmp)
            source = tmpdir / "clip.wav"
            output = tmpdir / "out.md"
            source.write_bytes(b"fake")
            env = self.base_env(tmpdir)
            self.add_fake_ffmpeg(tmpdir, env)
            result = subprocess.run(
                [
                    str(GENERATE_SCRIPT),
                    "--input",
                    str(source),
                    "--language",
                    "English",
                    "--locale",
                    "en-GB",
                    "--title",
                    "Manual Title",
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
            rendered = output.read_text(encoding="utf-8")
            self.assertIn("# Manual Title", rendered)
            self.assertIn("Locale: `en-GB`", rendered)

    def test_device_controls_are_forwarded_to_transcription(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmpdir = Path(tmp)
            source = tmpdir / "clip.wav"
            output = tmpdir / "out.md"
            source.write_bytes(b"fake")
            env = self.base_env(tmpdir)
            self.add_fake_ffmpeg(tmpdir, env)
            fake_transcribe = tmpdir / "fake-transcribe.sh"
            fake_transcribe.write_text(
                "#!/usr/bin/env bash\n"
                "printf '%s\\n' \"$@\" > \"$TRANSCRIBE_ARGS_LOG\"\n"
                "output=''\n"
                "previous=''\n"
                "for argument in \"$@\"; do\n"
                "  if [[ \"$previous\" == '--output' ]]; then output=\"$argument\"; fi\n"
                "  previous=\"$argument\"\n"
                "done\n"
                "printf '{\"schema_version\":1,\"engine\":\"mock\",\"locale\":\"en-US\",\"full_text\":\"ok\",\"segments\":[],\"timing_complete\":true}\\n' > \"$output\"\n"
                "printf '%s\\n' \"$output\"\n",
                encoding="utf-8",
            )
            fake_transcribe.chmod(0o755)
            env["LISTENKIT_TRANSCRIBE_AUDIO"] = str(fake_transcribe)
            env["TRANSCRIBE_ARGS_LOG"] = str(tmpdir / "transcribe-args.log")
            result = subprocess.run(
                [
                    str(GENERATE_SCRIPT),
                    "--input",
                    str(source),
                    "--language",
                    "English",
                    "--output",
                    str(output),
                    "--device",
                    "cuda",
                    "--compute-type",
                    "float16",
                    "--device-index",
                    "2",
                ],
                check=False,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            forwarded = (tmpdir / "transcribe-args.log").read_text(encoding="utf-8")
            self.assertIn("--device\ncuda\n", forwarded)
            self.assertIn("--compute-type\nfloat16\n", forwarded)
            self.assertIn("--device-index\n2\n", forwarded)

    def test_rejects_multiple_public_inputs(self) -> None:
        result = subprocess.run(
            [
                str(GENERATE_SCRIPT),
                "--url",
                "https://example.com/video",
                "--input",
                "/tmp/clip.wav",
                "--language",
                "Japanese",
                "--output",
                "/tmp/out.md",
            ],
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Exactly one of --url or --input is required", result.stderr)

    def test_rejects_url_only_options_with_local_input(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmpdir = Path(tmp)
            source = tmpdir / "clip.wav"
            source.write_bytes(b"fake")
            result = subprocess.run(
                [
                    str(GENERATE_SCRIPT),
                    "--input",
                    str(source),
                    "--language",
                    "Japanese",
                    "--output",
                    str(tmpdir / "out.md"),
                    "--write-info-json",
                ],
                check=False,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("only valid with --url", result.stderr)

    def test_rejects_removed_high_level_inputs(self) -> None:
        for removed_option in ["--audio-path", "--transcript-json", "--source-ref", "--base-name"]:
            with self.subTest(option=removed_option):
                result = subprocess.run(
                    [
                        str(GENERATE_SCRIPT),
                        removed_option,
                        "value",
                        "--language",
                        "Japanese",
                        "--output",
                        "/tmp/out.md",
                    ],
                    check=False,
                    text=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                )
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("not supported by cli/generate-markdown.sh", result.stderr)

    def test_url_import_failure_suggests_audio_hijack_fallback(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmpdir = Path(tmp)
            bin_dir = tmpdir / "bin"
            bin_dir.mkdir()
            (bin_dir / "ffmpeg").write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
            (bin_dir / "yt-dlp").write_text(
                "#!/usr/bin/env bash\necho 'mock yt-dlp failure' >&2\nexit 42\n",
                encoding="utf-8",
            )
            os.chmod(bin_dir / "ffmpeg", 0o755)
            os.chmod(bin_dir / "yt-dlp", 0o755)
            env = self.base_env(tmpdir)
            env["PATH"] = f"{bin_dir}:{env['PATH']}"
            result = subprocess.run(
                [
                    str(GENERATE_SCRIPT),
                    "--url",
                    "https://example.com/unsupported",
                    "--language",
                    "Japanese",
                    "--output",
                    str(tmpdir / "out.md"),
                ],
                check=False,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("mock yt-dlp failure", result.stderr)
            self.assertIn("Audio import failed", result.stderr)
            self.assertIn("Audio Hijack", result.stderr)
            self.assertIn("cli/generate-markdown.sh --input <recording>", result.stderr)
            self.assertIn("docs/audio-hijack.md", result.stderr)

    def test_local_import_failure_does_not_suggest_audio_hijack(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmpdir = Path(tmp)
            bin_dir = tmpdir / "bin"
            source = tmpdir / "clip.wav"
            source.write_bytes(b"fake")
            bin_dir.mkdir()
            (bin_dir / "ffmpeg").write_text(
                "#!/usr/bin/env bash\necho 'mock ffmpeg failure' >&2\nexit 42\n",
                encoding="utf-8",
            )
            os.chmod(bin_dir / "ffmpeg", 0o755)
            env = self.base_env(tmpdir)
            env["PATH"] = f"{bin_dir}:{env['PATH']}"
            result = subprocess.run(
                [
                    str(GENERATE_SCRIPT),
                    "--input",
                    str(source),
                    "--language",
                    "Japanese",
                    "--output",
                    str(tmpdir / "out.md"),
                ],
                check=False,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("mock ffmpeg failure", result.stderr)
            self.assertNotIn("Audio Hijack", result.stderr)


if __name__ == "__main__":
    unittest.main()
