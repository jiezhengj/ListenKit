# Entering a project

Before any substantive work:

1. Confirm the actual project root.
2. Read `docs/spec-kit/PROJECT_CONFIG.json`, `LOCAL_OVERRIDES.md`, `POLICY.md`, and `MANIFEST.json`.
3. Check `.specify/`. If it exists, recover its existing state and do not initialize again.
4. Classify the request as read-only/explanatory, extremely small and low-risk, governance maintenance, or substantive engineering.
5. When work involves the CLI, an integration, an extension, init, upgrade, rollback, or recovery, also read `REFERENCE.md` and `OPERATING_PROTOCOL.md`.
6. If the loaded global Policy provides `SPEC_KIT_GOVERNANCE_SOURCE`, run the local manager's read-only central Reference check once in the new session; if it does not, skip silently and do not search for one.

# Substantive task entry

Natural-language requests such as “按 Spec 制定方案”, “use Spec Kit”, “start a Feature”, or equivalent substantive design, plan, or implementation intent map to the governed workflow. Begin with Discovery; do not treat the wording as permission to skip directly to specification or plan.

For substantive engineering, the governed upstream Spec Kit lifecycle is the execution path:

`discovery → review discovery → specify → clarify → review specification → plan → review plan bundle → checklist → tasks → readiness audit → cold-start review → review task package → analyze → remediation when needed → implement → validate → converge → completion review`

The following rules are mandatory:

1. Before specification or application-code changes, inspect the brownfield system, create or resume the feature's Discovery ledger, and identify blocking questions and unapproved assumptions.
2. A conversation, design note, or user message is not a substitute for a Spec Kit artifact.
3. Stop for explicit user review of `DISCOVERY`, `SPECIFICATION`, `PLAN_BUNDLE`, `TASK_PACKAGE`, and required `REMEDIATION`; bind each decision to paths and current hashes in `REVIEW_LEDGER.json`.
4. User approval such as “the plan is acceptable” applies only to the named review object. This approval does not authorize direct code edits or approve a later artifact.
5. If the approved direction is missing from or inconsistent with the current spec, plan, or tasks, use the upstream Spec Kit workflow to update the artifact before implementing it. Do not have this governance package edit `.specify/**` or `specs/**`.
6. If the user is only discussing options and has not expressed implementation intent, remain in discussion and do not modify application files.
7. Before implementation, require the task readiness report, isolated cold-start report, and current `TASK_PACKAGE` approval. Each task must be a self-contained, single-result work package with explicit stop conditions.
8. Once artifacts and review evidence are current, implement only approved tasks. If scope, assumptions, risks, or affected components change, pause, mark dependent approval stale, and return to the appropriate artifact.
9. Do not report substantive work as complete until required `analyze`, `validate`, `converge`, and completion review have finished and all failures or unresolved items are disclosed.

The governance package does not replace the upstream Spec Kit executor. Its rules guide when the Agent must enter and remain in that workflow.

## Reference update handoff

A central Reference update first changes the governance and Agent-context layer through an approved plan. It does not directly change `.specify/**`, `specs/**`, specifications, plans, or tasks. After the governance layer is synchronized, inspect the current upstream artifacts and use the upstream Spec Kit workflow if they require alignment.

# Governance operations

For changes to this governance package itself, generate an operation plan before every mutation; the current operator then authorizes it with the exact plan ID and hash, after which the sole `apply-plan` may run.

If a native-integration target is unwritable, permission is insufficient, a sandbox blocks the work, managed-file repair fails, or installation fails, stop and return `NATIVE_INSTALL_BLOCKED`; do not switch to generic or another key.

For a lightweight CLI update reminder in an existing Spec Kit project without `docs/spec-kit/**`, use the separate `plan-install-update-reminder` plan with the exact existing context anchor. It adds only a Reference-owned managed reminder block and delegates the check to upstream `specify self check`; it does not create a governance package or modify upstream-owned artifacts.

If the project already has the runtime-selected project context anchor, it is a project-owned rules file. The governance loader may only be appended or updated inside its managed region; all other bytes must remain byte-identical. A loader file may be created only at the exact anchor path supplied and evidence-validated in an approved plan.

Before `plan-init`, ask the user which BCP-47 language tag should govern new or substantially rewritten project documentation. Pass the explicit selection as `--documentation-language <tag>` so it is stored in project configuration and written into the selected context anchor. Do not infer or mass-translate.

The project governance package is a shared team baseline and does not depend on personal global rules or a central Reference directory. Its context anchor contains separately managed governance-loader and Reference-update-check blocks. The central Reference may be used only for explicit update review.
