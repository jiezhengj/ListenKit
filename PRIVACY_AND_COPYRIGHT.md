# Privacy and Copyright

## Local Processing

The default ASR route performs local inference with MLX Whisper on a ready
Apple Silicon Mac and faster-whisper elsewhere. Audio transcription happens on
your machine, but the first run may download runtime dependencies and model
files unless they are already cached locally.

Apple Speech is an optional local backend on macOS. When the Apple helper is used, audio transcription also happens on the local Mac.

## AI Editing

The AI editing stage may send transcript text and metadata to the model provider used by your agent or editor. Do not process sensitive audio unless that is acceptable for your environment.

## Copyright

This project does not include copyrighted audio, transcripts, textbook content, or course materials.

You are responsible for ensuring you have the right to download, record, transcribe, and study any source material you process.

Do not use this project to redistribute copyrighted transcripts or audio.
