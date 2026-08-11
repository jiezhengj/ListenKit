# ListenKit Repository Instructions

Read `LLM_INTEGRATION.md` before using ListenKit as an external Agent or changing its public integration behavior. The provider-neutral summary is `adapters/agent/listenkit-agent-instructions.md`.

- Do not patch ListenKit source merely to work around an Agent sandbox, shell, stdout-capture, or PATH limitation. Use the project-provided Python or platform dispatcher and `--report-json` first.
- For automated use, prefer `python -m listenkit_cli <command>` from the repository root. If the host Python environment is uncertain, use `cli/listenkit.sh <command>` on macOS/Linux/WSL or `cli/listenkit.ps1 <command>` on native Windows.
- Normal transcript integrations call only `generate-markdown`; do not reimplement import, subtitle selection, ASR fallback, or rendering.
- Keep Agent-specific files as thin descriptions of the shared contract. Do not create provider-specific business logic.
- Repository changes must preserve Python 3.14 runtime isolation, UTF-8 I/O, transcript schema compatibility, atomic output writes, and non-interactive automation behavior.
- Before handing off code changes, run `python -m compileall -q listenkit_cli cli tools` and `python -m unittest discover -s tests -v`. Platform hardware and permission claims require matching real-device verification.
