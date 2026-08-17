# E329 - Synchronize Valid-Abort Tests With Launcher Termination

## Symptom

MPICH Buildbot reaches the `valid-int-max` PMI control after completing the
upstream test prefix, then the test package fails with a launcher return code
of 1. The production Hydra change deliberately removed the
`auto_cleanup == 0` early success return, but the test still requires the
launcher and all ranks to survive the abort, write a canary, finalize, and
return zero.

## Root Cause

The test oracle retained the old interpretation of
`-disable-auto-cleanup`: it treated the option as permission for an explicit
abort to continue normally. That expectation is incompatible with the fixed
production contract. Automatic cleanup policy may affect ordinary shutdown,
but a valid explicit abort must still terminate the launcher and job.

The nonzero result by itself is not enough to prove correctness. It could also
come from a PMI parser rejection, a crash, or incomplete cleanup, so the
replacement oracle must bind the exact path and its side effects.

## Solution

Run valid `INT_MIN` and `INT_MAX` controls through the same managed termination
contract used by the abort negatives:

1. Allow the expected nonzero launcher result only with required launcher
   cleanup enabled.
2. Before releasing the frame, bind exactly parent ranks 0 and 1 plus spawned
   rank 0, including each PID and PGID, and exactly one Hydra proxy.
3. Reject `unable to parse PMI command` so a parser failure cannot impersonate
   a valid abort.
4. Require the exact armed marker for the selected mode.
5. Delay the survival canary and require it to remain absent after termination.
6. Require zero launcher residue and finish with a fresh ordinary MPI smoke
   launch.

Do not restore the production early-success return merely to satisfy the old
test expectation.

## Validation

The directed validator passed both valid modes, four negative cases, all 26
single-fragment deletion mutations, and C11 `-Wall -Wextra -Werror`. Its result
SHA-256 is
`93df84e25ade8b321a7588a2c045b101f85a950824e29218eda2fbbcb02403b6`.

The complete 41-patch series also passed forward and reverse replay through
Git, GNU patch 2.7.6, and patch_ng. All three forward trees were identical and
all reverse trees matched the official source archive. The replay result
SHA-256 is
`72518c0a6415cca359b8783297abcc52ba91107fc2d92ec56df2bf7ed9eb2c9f`.

## Applicability

Use this rule when an explicit abort implementation changes termination
semantics and an older test still models option-controlled survival. It does
not authorize accepting arbitrary nonzero exits, parser failures, leaked
processes, or missing topology evidence, and it does not replace independent
W4 or exact-current-HEAD CI.
