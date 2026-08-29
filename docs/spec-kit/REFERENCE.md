# Runtime discovery

Use the installed runtime as authority:

```text
specify version
specify --help
specify integration --help
specify integration status --json
```

Project-aware integration commands require `.specify/`; never initialize a real project only to query list/search/info. Do not parse Rich output or import private CLI APIs.

# CLI and Agent integration are separate

Installing `specify` globally does not install Agent Skills. Let the CLI create and maintain project integrations. Do not manually copy generated Skills into global directories. For a concrete Agent, native integration is mandatory; native target failure is a blocker, never generic fallback.

The global CLI, project `.specify/` infrastructure, installed Agent integration,
extensions, presets, workflows, events, and project Skills are separate layers.
Installing or upgrading one layer does not imply that the others changed.

# Project state and lifecycle

`.specify/` means an existing Spec Kit project. Resume it, inspect `status --json`, and protect existing files. New substantive work uses:

`constitution → specify → clarify → plan → checklist → tasks → analyze → implement → validate → converge`

Invocation syntax belongs to the installed integration. Validation and convergence are completion gates.

The active feature comes from `.specify/feature.json` or the `SPECIFY_FEATURE_DIRECTORY` override, not from the checked-out Git branch. For an existing non-empty project, the upstream adoption command is `specify init --here --force --integration <key>`; protect a reviewable baseline and inspect the generated diff first. The governance manager may invoke that command through its approved external operation, but does not directly edit its output.

# Ownership and runtime independence

The upstream Spec Kit CLI owns `.specify/**`, `specs/**`, and the native Agent integration files it generates. This governance package may inspect those artifacts and may invoke supported upstream CLI commands, but it must not directly edit or replace them.

The Reference-owned additions in a target project are `docs/spec-kit/**`, `tools/spec-kit-governance/governance.py`, `.spec-kit-governance/**`, and the separately managed governance-loader and Reference-update-check blocks inside the selected context anchor. The central Reference repository and a globally deployed Policy are maintenance conveniences, not runtime prerequisites.

User approval such as “the plan is acceptable” is not an implementation bypass. For substantive work, first align the proposal with the current upstream Spec Kit specification, plan, and tasks; this approval does not authorize direct code edits before that alignment. Then implement through the upstream workflow. `verify` validates only the Reference-owned package, not feature completion.

# Integration lifecycle

Install a compatible additional integration with `specify integration install <key>` only through a plan. Use `specify integration use <key>` only in an explicitly approved default-change plan. Use `specify integration switch <key>` only when the plan lists exact replacement scope. After CLI upgrades, verify managed-file hashes and use supported integration upgrade mechanisms.

Non-interactive init must always include `--integration <key>`; omitting it can select an unrelated default. Do not use `init --force` as routine upgrade or repair.

`specify integration use <key>` changes the project's single default integration
and can affect default-sensitive extensions, presets, events, and shared
infrastructure. Treat it as a separately approved operation. Non-default
integration parity must be verified rather than assumed.

When the installed CLI exposes workflow init steps, the reviewed upstream range supports shell, PowerShell, and Python script variants. Use the installed CLI help for the exact option and default.

# Generic boundary

`generic` writes Markdown Commands to an explicitly supplied directory. It does not prove that an Agent reads that directory and is not a universal adapter. V1 allows it only with a current-version native-absence attestation, verified compatibility, empty installed integration set, project configuration approval and exact user plan approval.

If the CLI has a native integration for the current Agent, an unwritable target,
permission failure, sandbox restriction, or install failure is
`NATIVE_INSTALL_BLOCKED`; it is never a reason to use generic or another key.

# Upgrade and source of truth

For runtime mechanics: project state → installed integration → installed CLI → this Reference → central Reference → upstream. Upstream is evidence, not dynamically imported instructions. `NONE`/`REFERENCE`/`POLICY` classification requires human review; a project snapshot is the collaborator's offline baseline.

For CLI maintenance use the installed help and supported lifecycle commands:

```text
specify self check
specify self upgrade
specify integration upgrade <key>
specify extension update
```

# Central Reference update check

For a project that carries the committed governance package, the central Reference check is enabled only when the current Agent has loaded the global Policy and that Policy provides a readable `SPEC_KIT_GOVERNANCE_SOURCE` path. Before the first substantive task in a new session, run the local manager's read-only `check-update --source <central-reference-path>` at most once. If the Policy or locator is absent, skip silently; do not search the machine for a Reference directory.

`UP_TO_DATE` means the target manifest source revision matches the clean central Reference checkout. `UPDATE_AVAILABLE` means a clean, ancestor central source has newer Reference content. `REVIEW_REQUIRED` means the baseline is divergent or the change includes Policy content. These statuses never authorize mutation. The user must approve an exact `plan-upgrade` and `apply-plan` before Reference-owned files are synchronized.

Reference synchronization updates only `docs/spec-kit/**`, the local governance manager, and the managed block in the explicit context anchor. It does not update `.specify/**`, `specs/**`, native Agent files, or business code. After synchronization, the upstream Spec Kit workflow decides whether any specification, plan, or task artifacts need updating.

# Optional CLI update reminder

An already Spec Kit project may opt into a lightweight reminder without installing the project governance package. `plan-install-update-reminder` appends a separate managed block to the exact existing Agent context anchor and asks the Agent to run upstream `specify self check` once per session. It requires only the installed CLI, an existing `.specify/` directory, and the explicit anchor path. It does not create `docs/spec-kit/**`, copy the manager, or modify `.specify/**`, `specs/**`, or native integration files. A detected update is reported to the user; `specify self upgrade` still requires explicit approval.

For a substantive defect, use the installed project's bug workflow when the
bug extension is present; verify reproduction, remediation, and validation.
Do not report a bug as fixed merely because a command completed.

Bundles, presets, workflows, and events are runtime-managed artifacts. Inspect
their current status before changing them and do not claim that a non-default
integration received extension or preset artifacts unless status proves it.
