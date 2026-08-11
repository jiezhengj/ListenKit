# Output Format

Rendered transcript Markdown uses a fixed section contract:

```markdown
# Title

## Source

## Transcript
```

## Section Rules

- `Source`: source reference or audio filename, language, locale, transcript engine, actual ASR device and compute type when available, acceleration fallback reason when applicable, timing status, and generation time.
- `Transcript`: ASR text, lightly cleaned for spacing and paragraph breaks.

The format is plain Markdown. ListenKit does not add learning-analysis sections; downstream projects can transform the transcript into their own note format.

## Transcript JSON

Built-in backends emit schema version 1:

```json
{
  "schema_version": 1,
  "engine": "faster-whisper",
  "device": "cuda",
  "device_index": 0,
  "device_name": "NVIDIA GeForce RTX 4070",
  "compute_type": "float16",
  "locale": "ja-JP",
  "full_text": "...",
  "segments": [{"start": 0.0, "end": 1.2, "text": "..."}],
  "timing_complete": true
}
```

The required semantic fields are `engine`, `locale`, `full_text`, `segments`, and `timing_complete`. Readers accept older payloads without `schema_version` as legacy v1. They reject an explicit unknown schema version instead of guessing how to interpret it.

Faster-whisper payloads also report the selected `device`, `device_index`, and
`compute_type`. `device_name` is included when NVIDIA metadata is available. If
automatic CUDA execution falls back, `fallback_from` lists failed device/type
attempts and `fallback_reason` records the bounded diagnostic.

MLX Whisper payloads use `engine: "mlx-whisper"`, `device: "metal"`, device
index `0`, and `compute_type: "float16"`. Rendered Markdown includes actual
engine, device, and compute metadata. If automatic MLX selection is unavailable,
the resulting faster-whisper engine/device values make the executed fallback
path visible; CUDA attempt failures additionally use `fallback_from` and
`fallback_reason`.

## Execution Report JSON

`generate-markdown` and `transcribe-audio` accept `--report-json <path>`. The
execution report is a separate, atomic status artifact; it does not replace the
same-stem transcript JSON and intentionally omits full transcript text.

Successful example:

```json
{
  "schema_version": 1,
  "listenkit_version": "1.0.0",
  "command": "generate-markdown",
  "status": "ok",
  "started_at": "2026-08-10T10:00:00Z",
  "finished_at": "2026-08-10T10:00:08Z",
  "duration_seconds": 8.0,
  "outputs": {
    "markdown": "work/sample.md",
    "transcript_json": "work/sample.json"
  },
  "transcription": {
    "schema_version": 1,
    "engine": "mlx-whisper",
    "device": "metal",
    "compute_type": "float16",
    "locale": "en-US",
    "timing_complete": true
  }
}
```

On failure, `status` is `error` and an `error` object contains the exception
type and message. The report path must differ from both Markdown and transcript
JSON paths. Callers should treat unknown execution-report schema versions as
unsupported instead of guessing their meaning.
