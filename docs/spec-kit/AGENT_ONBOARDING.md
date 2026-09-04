# First-time Agent onboarding

1. The current Agent must provide a runtime ID and an exact integration key. A display name without a key returns `KEY_REQUIRED`.
2. Read `specify version` and `specify --help`; if the CLI is absent, request authorization and recommend `uv tool install specify-cli --from git+https://github.com/github/spec-kit.git@<approved-40-character-commit-sha>`. Do not install it silently, use a floating branch, or treat installation as proof that Agent-specific project files exist.
3. Run read-only `doctor` and `resolve-agent`. Do not treat a default, a PATH tool, a directory name, or a similar product as an identity.
4. When `.specify/` exists, run `specify integration status --json`. Reuse a healthy existing active binding; otherwise generate an onboarding plan.
5. When `.specify/` does not exist, complete the Agent-neutral governance bootstrap first, then generate a `plan-init` with an explicit integration. Omitting `--integration` is prohibited.
6. When the native integration is not installed, the plan uses `specify integration install <claimed-key>` without `--force`; multi-install safety is decided by the CLI gate.
7. For an external native install, pass each project-relative target prefix explicitly from the current CLI/runtime's reported integration metadata as `--allowed-path-prefix <prefix>`. The manager never guesses a Skills, Commands, or context directory. A missing or incomplete scope must stop the plan rather than broaden the prefix.
8. Any unwritable native target, permission, sandbox, repair, or installation error returns `NATIVE_INSTALL_BLOCKED`; preserve the existing state and stop.
9. A context anchor may come only from an active binding or from a project-relative path explicitly supplied by the user, and it must carry compatibility evidence through `plan-onboard --anchor-evidence <project-relative-json>`. Stop for an unknown or unsupported format.
10. Materialized delivery is allowed only when Loader fresh-session validation fails and the user explicitly requests it; `--loader-failure-evidence <project-relative-json>` must be supplied at the same time.
11. Perform the sole apply only after the user authorizes it with `apply-plan --approve-plan-id <id> --approve-plan-sha256 <hash>`.
12. In a new session, verify the anchor, Loader, Policy version, probe token, runtime ID, integration key, native workflow, and existing inventory; save project-relative verification evidence, then generate `plan-activate-binding`. Until that plan is applied, the binding may only be `provisional` and must not be reported as `READY`.

13. If the project already has the runtime-selected context anchor, onboarding may only inject or update the managed loader region; every byte outside that region must be preserved byte-for-byte. Overwriting, deleting, reordering, normalizing, or whole-file formatting is prohibited. If the anchor is absent, create only the exact runtime- or user-supplied path after evidence validation; never guess a filename.
14. Before `plan-init`, ask the user for the BCP-47 language tag for new or substantially rewritten project documentation. Pass it as `--documentation-language <tag>`. The manager stores the explicit selection in `PROJECT_CONFIG.json` and the selected context-anchor loader; it must not infer a language or mass-translate existing documents.
15. For project configuration v2, run the read-only companion status check and verify the exact installed `governed-sdd` workflow, discovery extension, tiny-model task preset, validator adapter, CLI compatibility range, and managed-file health. Missing capability returns `COMPANION_CAPABILITY_UNAVAILABLE`; do not report the governed workflow as ready.
16. Start a fresh Agent session and confirm that natural-language substantive intent maps to Discovery, that each human gate pauses, and that the Agent can read project-local review evidence without the central Reference or personal global Policy.
17. Verify that `docs/spec-kit/features/**` is treated as a preserved project-local subtree and is excluded from central template replacement, cleanup, and rollback deletion.

For an already Spec Kit project that does not install the full governance package, the optional `plan-install-update-reminder` operation can append only its separate managed reminder block to the exact existing context anchor. It requires the installed CLI, an existing `.specify/` directory, and the explicit anchor path; it does not create `docs/spec-kit/**` or modify upstream-owned artifacts.

# After onboarding

Onboarding establishes access to project rules and proves companion visibility; it does not authorize or complete Feature work. For substantive work, user approval applies only to the identified review object and current hashes. It does not authorize direct code edits before Discovery, specification, plan bundle, and task package approvals are current. The Reference package must not modify `.specify/**`, `specs/**`, or native Agent-generated integration files.
