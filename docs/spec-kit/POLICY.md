# Scope

GitHub Spec Kit is used for substantive software engineering work. Read-only investigation, explanation, extremely small typo fixes, and very low-risk minor changes do not require the full lifecycle.

# Conversation approval and implementation boundary

For substantive work, the upstream Spec Kit artifacts are the implementation contract. A conversation, design note, or user message is not itself a spec, plan, task list, or completion record.

User approval phrases such as “the plan is acceptable” or “proceed with this approach” approve the discussed direction only. They authorize the Agent to advance that direction into the upstream Spec Kit workflow; this approval does not authorize direct application-code edits that skip artifact alignment.

When an approved direction is missing from or inconsistent with the current specification, plan, or tasks, the Agent must first use the upstream Spec Kit workflow to update the relevant artifacts. The Reference governance package must never edit `.specify/**`, `specs/**`, or native Agent-generated integration files to enforce this policy.

If the user is only discussing alternatives and has not expressed implementation intent, the Agent must remain in discussion. If implementation intent exists, the Agent may proceed automatically after artifact alignment without requiring the user to repeat “use Spec Kit”.

If implementation reveals a changed requirement, assumption, risk, public contract, data boundary, or affected component, the Agent must pause, update the upstream Spec Kit artifacts, and then resume from the resulting tasks. It must not silently expand the implementation scope.

# Projects and brownfields

Before making a change, confirm the actual project root; read every applicable project-local rule, README, architecture document, test, dependency, and CI configuration; understand the actual brownfield system; and protect existing user work. When `.specify/` exists, restore the existing project state and do not routinely reinitialize it.

If the project already has the runtime-selected project context anchor, it is collaboratively maintained project rule content. The Spec Kit loader may be appended to or updated inside that file only through a reviewed manager plan; every byte outside the managed region must be preserved byte-for-byte. The manager may create only the exact anchor path supplied and evidence-validated by the current Agent runtime or user. It must never guess, replace, delete, reorder, normalize, or overwrite an anchor.

Before first-time Spec Kit initialization, ask the user for the BCP-47 language tag for new and substantially rewritten project documentation. Pass the explicit value to `plan-init`, store it in `PROJECT_CONFIG.json`, and render the corresponding rule in the selected context anchor. Never infer it from locale, Agent identity, existing documents, or a default; do not mass-translate existing documents.

# Agent-neutral operation and native integrations

The governance package does not enumerate Agent products in advance. The current Agent must have its runtime ID and exact integration key explicitly declared by the user, host, or Agent runtime; a display name cannot produce a mutation plan. Do not infer identity from PATH, directory names, a default integration, similar product names, or Rich catalog output.

When the current CLI provides a native integration for the current Agent, that native integration is mandatory. An unwritable Skills/Commands target or parent directory, insufficient permission, a sandbox block, managed-file repair failure, or CLI installation failure is `NATIVE_INSTALL_BLOCKED`. Do not downgrade to generic, use another key, or report completion because of convenience, permissions, paths, or conflicts. A binding may be `active` only after fresh-session verification confirms the runtime ID/key match, the context anchor is loaded, and managed files are healthy.

Generic is allowed only when the current CLI has no native integration, project configuration permits it, the current version has a human-reviewed native-absence attestation, the target Agent is compatible with the generic Markdown Commands contract, the project's installed integration set is empty, and the user approves the exact plan. Generic must be marked as non-native and limited support.

# Spec Kit state and lifecycle

New projects must use explicit `specify init --here --non-interactive --integration <approved-key>`. If a non-interactive init omits the key, the CLI may select a default product, so the manager must reject that command. In a non-empty brownfield, `--force` may appear only in a dedicated `plan-init`, with rehearsal, a scope snapshot, backup, exact authorization, and failure recovery; no other command may use `--force`.

Substantive work follows:

`constitution → specify → clarify → plan → checklist → tasks → analyze → implement → validate → converge`

Clarify and checklist may be skipped only when the applicable risk assessment supports the skip and the Agent states the reason. Analyze, validate, and converge are required before substantive completion. Implementation must remain synchronized with the accepted specification, plan, tasks, project constraints, and tests.

# Default and integration coexistence

The project default integration uses a pinned strategy. Routine onboarding must not change the default. A default change may update configuration only after project configuration opens a one-time change window, an independent plan is generated, `specify integration use <key>` is run, and status verification succeeds; failure must restore the prior default. Extensions, presets, events, and shared infrastructure of non-default integrations must be verified separately; do not claim parity.

# Authority order

The policy authority order is: current user instructions, higher-priority runtime rules, safety rules, every applicable project-local rule, project `LOCAL_OVERRIDES.md`, project `POLICY.md`, personal global Bootstrap, project `REFERENCE.md`, personal central Reference, and upstream documentation.

The runtime-fact order is: current-project `.specify/`, installed integrations and manifests, the installed CLI, project `REFERENCE.md`, personal central Reference, and upstream documentation. When runtime facts conflict with the project snapshot, the runtime prevails and the discrepancy must be recorded.

# Validation, upgrades, and completion

Relevant tests, builds, linting, schemas, reproductions, validation, and convergence must be run; failures must not be concealed. The CLI, integrations, extensions, governance package, and Skills are separate layers, and upgrading one layer must not assume that the others upgrade automatically. Central upstream changes must be classified as `NONE`, `REFERENCE`, or `POLICY`; the checker is read-only, the baseline advances last after review, and upstream history must not be merged or Policy automatically deployed.

Completion requires agreement among user intent, accepted artifacts, implementation, project constraints, validation, convergence, the native integration, adapter verification, and capability-inventory conservation. Approval of a conversational proposal is not completion evidence. Do not report completion when a blocker, unmapped legacy capability, unplanned deletion, downgrade, invalid state, or default change exists; artifact drift is also unresolved work.

# Central Reference maintenance

When the global Policy is actually loaded and provides a readable `SPEC_KIT_GOVERNANCE_SOURCE`, an existing `.specify/` project with this committed governance package may perform one read-only central Reference check before the first substantive task in a new Agent session. If the global Policy, source locator, or source verification is absent, skip the check silently and never scan the computer for a Reference directory.

A verified Reference update is a notification, not permission to edit the project. After explicit approval, synchronize only the Reference-owned governance package, manager, and managed context-anchor block through `plan-upgrade` and `apply-plan`. Never update `.specify/**`, `specs/**`, native Agent files, or business code as part of this sync.

After synchronization, inspect the current upstream Spec Kit artifacts and let the upstream workflow decide whether a specification, plan, task list, or other Spec artifact needs updating. A Reference update is not evidence that any such artifact is stale.
