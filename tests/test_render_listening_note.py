import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
RENDER_SCRIPT = REPO_ROOT / "cli" / "render-listening-note.py"


class RenderListeningNoteTests(unittest.TestCase):
    def run_payload(self, payload: dict) -> subprocess.CompletedProcess[str]:
        tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(tmpdir.cleanup)
        root = Path(tmpdir.name)
        transcript = root / "transcript.json"
        output = root / "note.md"
        transcript.write_text(json.dumps(payload), encoding="utf-8")
        return subprocess.run(
            [
                sys.executable,
                str(RENDER_SCRIPT),
                "--audio-path",
                str(root / "sample.m4a"),
                "--transcript-json",
                str(transcript),
                "--title",
                "Schema Test",
                "--language",
                "Japanese",
                "--output",
                str(output),
            ],
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

    def render_sample(self, sample_name: str, language: str) -> str:
        with tempfile.TemporaryDirectory() as tmpdir:
            output = Path(tmpdir) / "note.md"
            transcript = REPO_ROOT / "examples" / sample_name
            result = subprocess.run(
                [
                    sys.executable,
                    str(RENDER_SCRIPT),
                    "--audio-path",
                    str(Path(tmpdir) / "sample.m4a"),
                    "--transcript-json",
                    str(transcript),
                    "--title",
                    "Sample Note",
                    "--language",
                    language,
                    "--output",
                    str(output),
                ],
                check=False,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            return output.read_text(encoding="utf-8")

    def test_renders_required_sections_for_japanese(self) -> None:
        rendered = self.render_sample("sample-transcript-ja.json", "Japanese")
        for heading in [
            "# Sample Note",
            "## Source",
            "## Transcript",
        ]:
            self.assertIn(heading, rendered)
        removed_headings = [
            "## " + "Listening " + "Focus",
            "## " + "Useful " + "Expressions",
            "## " + "Study " + "Plan",
        ]
        for removed_heading in removed_headings:
            self.assertNotIn(removed_heading, rendered)
        self.assertIn("今日は駅の近くにある小さな喫茶店", rendered)
        self.assertIn("Locale: `ja-JP`", rendered)

    def test_renders_required_sections_for_english(self) -> None:
        rendered = self.render_sample("sample-transcript-en.json", "English")
        self.assertIn("Today I want to talk about a small library", rendered)
        self.assertIn("Locale: `en-US`", rendered)

    def test_rejects_missing_required_transcript_key(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            bad_json = Path(tmpdir) / "bad.json"
            bad_json.write_text(json.dumps({"engine": "apple"}), encoding="utf-8")
            output = Path(tmpdir) / "note.md"
            result = subprocess.run(
                [
                    sys.executable,
                    str(RENDER_SCRIPT),
                    "--audio-path",
                    str(Path(tmpdir) / "sample.m4a"),
                    "--transcript-json",
                    str(bad_json),
                    "--title",
                    "Bad",
                    "--language",
                    "English",
                    "--output",
                    str(output),
                ],
                check=False,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("missing required keys", result.stderr)

    def test_rejects_transcript_error_payload(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            bad_json = Path(tmpdir) / "error.json"
            output = Path(tmpdir) / "note.md"
            bad_json.write_text(
                json.dumps(
                    {
                        "error": {"type": "mock_error", "message": "transcription failed"},
                        "engine": "faster-whisper",
                        "locale": "ja-JP",
                        "full_text": "",
                        "segments": [],
                        "timing_complete": False,
                    }
                ),
                encoding="utf-8",
            )
            result = subprocess.run(
                [
                    sys.executable,
                    str(RENDER_SCRIPT),
                    "--audio-path",
                    str(Path(tmpdir) / "sample.m4a"),
                    "--transcript-json",
                    str(bad_json),
                    "--title",
                    "Bad",
                    "--language",
                    "Japanese",
                    "--output",
                    str(output),
                ],
                check=False,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("Transcript JSON contains ASR error", result.stderr)
            self.assertIn("mock_error", result.stderr)
            self.assertFalse(output.exists())

    def test_accepts_schema_version_one(self) -> None:
        result = self.run_payload(
            {
                "schema_version": 1,
                "engine": "faster-whisper",
                "locale": "ja-JP",
                "full_text": "正常です。",
                "segments": [],
                "timing_complete": True,
            }
        )

        self.assertEqual(result.returncode, 0, result.stderr)

    def test_renders_acceleration_metadata_and_fallback_reason(self) -> None:
        result = self.run_payload(
            {
                "schema_version": 1,
                "engine": "faster-whisper",
                "locale": "en-US",
                "device": "cpu",
                "compute_type": "int8",
                "fallback_reason": "CUDA runtime unavailable",
                "full_text": "fallback recorded",
                "segments": [],
                "timing_complete": True,
            }
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        output = Path(result.stdout.strip())
        rendered = output.read_text(encoding="utf-8")
        self.assertIn("ASR device: `cpu`", rendered)
        self.assertIn("Compute type: `int8`", rendered)
        self.assertIn("Acceleration fallback: CUDA runtime unavailable", rendered)

    def test_accepts_legacy_payload_without_schema_version(self) -> None:
        result = self.run_payload(
            {
                "engine": "apple",
                "locale": "ja-JP",
                "full_text": "legacy",
                "segments": [],
                "timing_complete": True,
            }
        )

        self.assertEqual(result.returncode, 0, result.stderr)

    def test_rejects_unknown_schema_version(self) -> None:
        result = self.run_payload(
            {
                "schema_version": 2,
                "engine": "faster-whisper",
                "locale": "ja-JP",
                "full_text": "future",
                "segments": [],
                "timing_complete": True,
            }
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Unsupported transcript schema_version: 2", result.stderr)


if __name__ == "__main__":
    unittest.main()
