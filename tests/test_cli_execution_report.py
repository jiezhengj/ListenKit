import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from listenkit_cli.cli import main
from listenkit_cli.errors import ListenKitError


class CliExecutionReportTests(unittest.TestCase):
    def test_transcribe_success_writes_machine_readable_report(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            audio = root / "sample.wav"
            output = root / "transcript.json"
            report = root / "execution.json"
            audio.write_bytes(b"fake")
            transcript = {
                "schema_version": 1,
                "engine": "mlx-whisper",
                "device": "metal",
                "compute_type": "float16",
                "locale": "en-US",
                "full_text": "hello",
                "segments": [],
                "timing_complete": True,
            }

            def fake_transcribe(**kwargs):
                kwargs["output"].write_text(
                    json.dumps(transcript, ensure_ascii=False), encoding="utf-8"
                )
                return kwargs["output"]

            with mock.patch(
                "listenkit_cli.cli.transcribe_audio", side_effect=fake_transcribe
            ), contextlib.redirect_stdout(io.StringIO()):
                status = main(
                    [
                        "transcribe-audio",
                        "--audio-path",
                        str(audio),
                        "--locale",
                        "en-US",
                        "--output",
                        str(output),
                        "--report-json",
                        str(report),
                    ]
                )

            self.assertEqual(status, 0)
            payload = json.loads(report.read_text(encoding="utf-8"))
            self.assertEqual(payload["schema_version"], 1)
            self.assertEqual(payload["command"], "transcribe-audio")
            self.assertEqual(payload["status"], "ok")
            self.assertEqual(payload["outputs"]["transcript_json"], str(output))
            self.assertEqual(payload["transcription"]["device"], "metal")
            self.assertNotIn("full_text", payload["transcription"])

    def test_generate_success_reports_both_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "sample.wav"
            output = root / "sample.md"
            transcript_path = output.with_suffix(".json")
            report = root / "execution.json"
            source.write_bytes(b"fake")

            def fake_generate(**kwargs):
                kwargs["output"].write_text("# Sample\n", encoding="utf-8")
                transcript_path.write_text(
                    json.dumps(
                        {
                            "schema_version": 1,
                            "engine": "faster-whisper",
                            "device": "cpu",
                            "compute_type": "int8",
                            "locale": "en-US",
                            "full_text": "hello",
                            "segments": [],
                            "timing_complete": True,
                        }
                    ),
                    encoding="utf-8",
                )
                return kwargs["output"]

            with mock.patch(
                "listenkit_cli.cli.generate_markdown", side_effect=fake_generate
            ), contextlib.redirect_stdout(io.StringIO()):
                status = main(
                    [
                        "generate-markdown",
                        "--input",
                        str(source),
                        "--language",
                        "English",
                        "--output",
                        str(output),
                        "--report-json",
                        str(report),
                    ]
                )

            self.assertEqual(status, 0)
            payload = json.loads(report.read_text(encoding="utf-8"))
            self.assertEqual(payload["status"], "ok")
            self.assertEqual(payload["outputs"]["markdown"], str(output))
            self.assertEqual(
                payload["outputs"]["transcript_json"], str(transcript_path)
            )

    def test_failure_writes_error_report(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            audio = root / "sample.wav"
            report = root / "execution.json"
            audio.write_bytes(b"fake")
            stderr = io.StringIO()
            with mock.patch(
                "listenkit_cli.cli.transcribe_audio",
                side_effect=ListenKitError("backend unavailable"),
            ), contextlib.redirect_stderr(stderr):
                status = main(
                    [
                        "transcribe-audio",
                        "--audio-path",
                        str(audio),
                        "--locale",
                        "en-US",
                        "--report-json",
                        str(report),
                    ]
                )

            self.assertEqual(status, 1)
            payload = json.loads(report.read_text(encoding="utf-8"))
            self.assertEqual(payload["status"], "error")
            self.assertEqual(payload["error"]["type"], "ListenKitError")
            self.assertIn("backend unavailable", payload["error"]["message"])

    def test_report_cannot_overwrite_transcript_output(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            audio = root / "sample.wav"
            output = root / "transcript.json"
            audio.write_bytes(b"fake")
            output.write_text("preserve me", encoding="utf-8")
            with contextlib.redirect_stderr(io.StringIO()):
                status = main(
                    [
                        "transcribe-audio",
                        "--audio-path",
                        str(audio),
                        "--locale",
                        "en-US",
                        "--output",
                        str(output),
                        "--report-json",
                        str(output),
                    ]
                )
            self.assertEqual(status, 1)
            self.assertEqual(output.read_text(encoding="utf-8"), "preserve me")

    def test_report_write_failure_returns_clean_cli_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            audio = root / "sample.wav"
            blocked_parent = root / "not-a-directory"
            audio.write_bytes(b"fake")
            blocked_parent.write_text("blocked\n", encoding="utf-8")
            stdout = io.StringIO()
            stderr = io.StringIO()

            with mock.patch(
                "listenkit_cli.cli.transcribe_audio",
                return_value='{"schema_version": 1, "engine": "apple"}',
            ), contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                status = main(
                    [
                        "transcribe-audio",
                        "--audio-path",
                        str(audio),
                        "--locale",
                        "en-US",
                        "--report-json",
                        str(blocked_parent / "execution.json"),
                    ]
                )

            self.assertEqual(status, 1)
            self.assertEqual(stdout.getvalue(), "")
            self.assertIn("Unable to write execution report", stderr.getvalue())
            self.assertNotIn("Traceback", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
