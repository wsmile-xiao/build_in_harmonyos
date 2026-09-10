# E2182-draft-A7F3 - HMDFS parent writability is not task-root readiness

## Problem pattern

An OpenHarmony W3 preflight can report `test -w` success on an HMDFS parent and
show group-writable mode bits, while `mkdir` for the exact new task root still
returns `Operation not permitted`. Replacing a multi-path `mkdir -p` with one
plain `mkdir`, or changing the umask alone, does not establish that this parent
accepts new directories from the current `hishell_hap` session.

## Root cause

`test -w` and `stat` evaluate discretionary access metadata. They do not prove
the path-specific HMDFS/HMMAC authorization for the child-creation operation.
Endpoint membership, SSH login, parent mode bits, and exact task-root creation
are therefore four distinct facts.

## Reusable resolution

1. Bind endpoint, host key, boot ID, UID, run ID and the exact proposed root
   before the first remote mutation.
2. Make create-new root creation a recorded transaction phase. Preserve shared
   group traversal with `umask 007`, but do not treat the umask as authorization.
3. On a clear `mkdir` failure, use the frozen status entry to prove the root is
   absent. Record `W3=NOT_RUN`, `launch_count=0`, and zero transfers.
4. Create a new run/root/freeze at a task-owned parent whose exact root creation
   succeeds. Never replay the failed run or borrow another task's directory.
5. Continue with exact-byte transfer, prepare and the sole launch only after the
   new root phase succeeds.

## Evidence

Two GLM successors under `currentUser/Download` returned EPERM at root creation
although the parent was mode `2771`, its group was present in the session, and
`test -w` returned yes. Both roots remained absent and both launch counts stayed
zero. A create-new successor directly under `currentUser` created its root and
transferred the frozen payload. The final independent r005 completed transfer,
native self-sign, one launch, receipt chain 10/10, state assertions 4/4,
consumer 1/1, release, and post-release absence.

## Applicability and safety

This applies to task-private W3 roots created on HMDFS from a `hishell_hap` SSH
session. It does not authorize chmod on shared parents, scanning or deleting
foreign roots, repeated probes in one run, or cross-run evidence assembly. A
failed root phase remains NOT_RUN even if a later successor passes.
