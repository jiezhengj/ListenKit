import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
EXPORT_SCRIPT = REPO_ROOT / "cli" / "export-audio-slices.py"


class ExportAudioSlicesTests(unittest.TestCase):
    def run_export(
        self,
        manifest,
        *,
        allow_overlap=False,
        overwrite=False,
        ffmpeg_exit=0,
        duration="10.0",
        padding="0.15",
    ):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        bin_dir = root / "bin"
        output_dir = root / "out"
        source = root / "recording.mp3"
        manifest_path = root / "slices.json"
        ffmpeg_log = root / "ffmpeg.log"
        bin_dir.mkdir()
        source.write_bytes(b"audio")
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
        self.write_fake_audio_tools(bin_dir, ffmpeg_exit=ffmpeg_exit, duration=duration)

        env = os.environ.copy()
        env["PATH"] = f"{bin_dir}{os.pathsep}{env['PATH']}"
        env["FFMPEG_LOG"] = str(ffmpeg_log)
        command = [
            sys.executable,
            str(EXPORT_SCRIPT),
            "--input",
            str(source),
            "--manifest",
            str(manifest_path),
            "--output-dir",
            str(output_dir),
            "--padding-seconds",
            padding,
        ]
        if allow_overlap:
            command.append("--allow-overlap")
        if overwrite:
            command.append("--overwrite")
        result = subprocess.run(
            command,
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
        )
        return root, output_dir, ffmpeg_log, result

    def write_fake_audio_tools(self, bin_dir: Path, *, ffmpeg_exit: int, duration: str) -> None:
        if os.name == "nt":
            (bin_dir / "ffprobe.cmd").write_text(f"@echo off\r\necho {duration}\r\n", encoding="utf-8")
            (bin_dir / "ffmpeg.cmd").write_text(
                "@echo off\r\n"
                ">> \"%FFMPEG_LOG%\" echo %*\r\n"
                f"if not \"{ffmpeg_exit}\"==\"0\" exit /b {ffmpeg_exit}\r\n"
                "set \"last=\"\r\n"
                ":loop\r\n"
                "if \"%~1\"==\"\" goto done\r\n"
                "set \"last=%~1\"\r\n"
                "shift\r\n"
                "goto loop\r\n"
                ":done\r\n"
                "> \"%last%\" echo slice\r\n",
                encoding="utf-8",
            )
            return

        (bin_dir / "ffprobe").write_text(
            f"#!/usr/bin/env bash\nprintf '{duration}\\n'\n",
            encoding="utf-8",
        )
        (bin_dir / "ffmpeg").write_text(
            "#!/usr/bin/env bash\n"
            "printf '%s\\n' \"$@\" >> \"$FFMPEG_LOG\"\n"
            f"if [[ {ffmpeg_exit} -ne 0 ]]; then exit {ffmpeg_exit}; fi\n"
            "printf 'slice' > \"${@: -1}\"\n",
            encoding="utf-8",
        )
        os.chmod(bin_dir / "ffprobe", 0o755)
        os.chmod(bin_dir / "ffmpeg", 0o755)

    def test_exports_multiple_slices_with_padding_and_json_report(self):
        root, output_dir, log, result = self.run_export(
            {
                "version": 1,
                "slices": [
                    {"id": "S01", "start": 0.10, "end": 1.00},
                    {"id": "S02", "start": 1.20, "end": 2.00},
                ],
            }
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["version"], 1)
        self.assertEqual(payload["source"], str(root / "recording.mp3"))
        self.assertEqual([item["id"] for item in payload["slices"]], ["S01", "S02"])
        self.assertEqual(payload["slices"][0]["start"], 0.0)
        self.assertEqual(payload["slices"][0]["end"], 1.1)
        self.assertEqual(payload["slices"][0]["overlap_with_previous_seconds"], 0.0)
        self.assertEqual(payload["slices"][1]["start"], 1.1)
        self.assertEqual(payload["slices"][1]["end"], 2.15)
        self.assertEqual(payload["slices"][1]["overlap_with_previous_seconds"], 0.0)
        self.assertTrue((output_dir / "recording_S01.m4a").read_bytes())
        self.assertTrue((output_dir / "recording_S02.m4a").read_bytes())
        argv = log.read_text(encoding="utf-8")
        self.assertRegex(argv, r"-ss\s+0\.0")
        self.assertRegex(argv, r"-to\s+1\.1")

    def test_allow_overlap_preserves_full_padding_and_reports_overlap(self):
        _, _, _, result = self.run_export(
            {
                "version": 1,
                "slices": [
                    {"id": "S01", "start": 1.0, "end": 2.0},
                    {"id": "S02", "start": 2.6, "end": 3.6},
                ],
            },
            allow_overlap=True,
            padding="0.5",
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        first, second = json.loads(result.stdout)["slices"]
        self.assertEqual(first["start"], 0.5)
        self.assertEqual(first["end"], 2.5)
        self.assertEqual(second["start"], 2.1)
        self.assertAlmostEqual(second["overlap_with_previous_seconds"], 0.4)

    def test_rejects_duplicate_ids(self):
        _, _, _, result = self.run_export(
            {
                "version": 1,
                "slices": [
                    {"id": "S01", "start": 0.0, "end": 1.0},
                    {"id": "S01", "start": 2.0, "end": 3.0},
                ],
            }
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Duplicate slice id", result.stderr)

    def test_rejects_overlapping_ranges(self):
        _, _, _, result = self.run_export(
            {
                "version": 1,
                "slices": [
                    {"id": "S01", "start": 0.0, "end": 2.0},
                    {"id": "S02", "start": 1.5, "end": 3.0},
                ],
            }
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("overlaps the previous slice", result.stderr)

    def test_rejects_existing_output_without_overwrite(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        source = root / "recording.mp3"
        source.write_bytes(b"audio")
        manifest = root / "slices.json"
        manifest.write_text(
            json.dumps({"version": 1, "slices": [{"id": "S01", "start": 0.0, "end": 1.0}]}),
            encoding="utf-8",
        )
        output_dir = root / "out"
        output_dir.mkdir()
        (output_dir / "recording_S01.m4a").write_bytes(b"old")

        result = subprocess.run(
            [
                sys.executable,
                str(EXPORT_SCRIPT),
                "--input",
                str(source),
                "--manifest",
                str(manifest),
                "--output-dir",
                str(output_dir),
            ],
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Output already exists", result.stderr)

    def test_surfaces_ffmpeg_failure(self):
        _, output_dir, _, result = self.run_export(
            {"version": 1, "slices": [{"id": "S01", "start": 0.0, "end": 1.0}]},
            ffmpeg_exit=42,
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("ffmpeg failed for S01", result.stderr)
        self.assertFalse((output_dir / "recording_S01.m4a").exists())

    def test_overwrite_replaces_existing_output(self):
        root, output_dir, _, first = self.run_export(
            {"version": 1, "slices": [{"id": "S01", "start": 0.0, "end": 1.0}]},
            overwrite=True,
        )
        self.assertEqual(first.returncode, 0, first.stderr)
        output = output_dir / "recording_S01.m4a"
        output.write_bytes(b"old")
        manifest = root / "slices.json"
        bin_dir = root / "bin"
        env = os.environ.copy()
        env["PATH"] = f"{bin_dir}{os.pathsep}{env['PATH']}"
        env["FFMPEG_LOG"] = str(root / "ffmpeg.log")

        second = subprocess.run(
            [
                sys.executable,
                str(EXPORT_SCRIPT),
                "--input",
                str(root / "recording.mp3"),
                "--manifest",
                str(manifest),
                "--output-dir",
                str(output_dir),
                "--overwrite",
            ],
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
        )

        self.assertEqual(second.returncode, 0, second.stderr)
        self.assertEqual(output.read_text(encoding="utf-8").strip(), "slice")

    def test_padding_does_not_exceed_audio_duration(self):
        _, _, _, result = self.run_export(
            {"version": 1, "slices": [{"id": "S01", "start": 9.0, "end": 9.95}]},
            duration="10.0",
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["slices"][0]["end"], 10.0)


if __name__ == "__main__":
    unittest.main()
