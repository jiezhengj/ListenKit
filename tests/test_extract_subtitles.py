import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
EXTRACT_SCRIPT = REPO_ROOT / "cli" / "extract-subtitles.sh"


@unittest.skipIf(os.name == "nt", "Bash wrapper compatibility is tested on Unix CI")
class ExtractSubtitlesTests(unittest.TestCase):
    def run_extract(self, tmpdir: Path, ytdlp_script: str) -> subprocess.CompletedProcess[str]:
        bin_dir = tmpdir / "bin"
        output = tmpdir / "transcript.json"
        bin_dir.mkdir()
        (bin_dir / "yt-dlp").write_text(ytdlp_script, encoding="utf-8")
        os.chmod(bin_dir / "yt-dlp", 0o755)
        env = os.environ.copy()
        env["PATH"] = f"{bin_dir}:{env['PATH']}"
        return subprocess.run(
            [
                str(EXTRACT_SCRIPT),
                "--url",
                "https://example.com/video",
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

    def test_manual_vtt_generates_transcript_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmpdir = Path(tmp)
            result = self.run_extract(
                tmpdir,
                """#!/usr/bin/env bash
paths=""
prev=""
for arg in "$@"; do
  if [[ "$prev" == "--paths" ]]; then paths="$arg"; fi
  prev="$arg"
done
mkdir -p "$paths"
cat > "$paths/subtitle.ja.vtt" <<'VTT'
WEBVTT

00:00:01.000 --> 00:00:02.500
こんにちは

00:00:03.000 --> 00:00:04.000
世界
VTT
""",
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads((tmpdir / "transcript.json").read_text(encoding="utf-8"))
            self.assertEqual(payload["schema_version"], 1)
            self.assertEqual(payload["engine"], "yt-dlp-subtitles")
            self.assertEqual(payload["subtitle_kind"], "manual")
            self.assertEqual(payload["locale"], "ja-JP")
            self.assertEqual(payload["full_text"], "こんにちは\n世界")
            self.assertTrue(payload["timing_complete"])
            self.assertEqual(payload["segments"][0]["start"], 1.0)
            self.assertEqual(payload["segments"][0]["end"], 2.5)

    def test_auto_captions_are_used_when_manual_subtitles_are_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmpdir = Path(tmp)
            result = self.run_extract(
                tmpdir,
                """#!/usr/bin/env bash
mode=""
paths=""
prev=""
for arg in "$@"; do
  if [[ "$arg" == "--write-subs" ]]; then mode="manual"; fi
  if [[ "$arg" == "--write-auto-subs" ]]; then mode="auto"; fi
  if [[ "$prev" == "--paths" ]]; then paths="$arg"; fi
  prev="$arg"
done
if [[ "$mode" == "manual" ]]; then
  exit 1
fi
mkdir -p "$paths"
cat > "$paths/subtitle.ja.vtt" <<'VTT'
WEBVTT

00:00:01.000 --> 00:00:02.000
自動字幕
VTT
""",
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads((tmpdir / "transcript.json").read_text(encoding="utf-8"))
            self.assertEqual(payload["subtitle_kind"], "auto")
            self.assertEqual(payload["full_text"], "自動字幕")

    def test_no_subtitles_returns_failure_without_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmpdir = Path(tmp)
            result = self.run_extract(
                tmpdir,
                "#!/usr/bin/env bash\nexit 1\n",
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("No usable subtitles found", result.stderr)
            self.assertFalse((tmpdir / "transcript.json").exists())


if __name__ == "__main__":
    unittest.main()
