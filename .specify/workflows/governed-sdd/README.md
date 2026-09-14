# Governed workflow

`governed-sdd` is a new workflow ID. It does not replace the upstream bundled `speckit` workflow.

It intentionally pauses at every human gate in non-interactive execution. To resume a paused run, the user must first review the named artifact, use the governance manager to append the matching hash-bound ledger event, and then supply the relevant `review_*` input as `approve`. Supplying an input only resolves the workflow gate; it is not approval evidence by itself.

The workflow dispatches `speckit.governance-discovery.*` commands supplied by the companion extension and `speckit.tasks` supplied by the tiny-model preset. The extension and preset must therefore be installed and registered for the active native integration before this workflow is run.

# Revision behavior

Spec Kit 1.0.4 gates can pause or abort, but cannot route a rejected gate back to a previous arbitrary command. A rejection therefore aborts the run deliberately. The operator corrects the artifact using the relevant command, records no approval until it is ready, and starts a new governed run or resumes only when the run state and artifact hashes remain valid. The governance manager is responsible for rejecting stale hashes.
