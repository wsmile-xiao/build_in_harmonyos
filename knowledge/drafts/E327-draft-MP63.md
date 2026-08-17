# E327 - Gate MPICH Detached-Descendant Canaries After Cleanup

## Symptom

An MPI process-control test deliberately creates a double-forked,
session-detached descendant. The managed launcher exceeds its finite budget and
reports `managed MPI command exceeded 15 seconds`, even though the runner's
timeout path has already cleaned its bound process identities.

An initial correction accepted that exact timeout, but the detached process
wrote its canary four seconds after startup while timeout cleanup could not
begin until 15 seconds. The next device run therefore rejected a canary that
proved only pre-cleanup lifetime, not post-cleanup escape.

## Root Cause

Hydra can keep the launcher active while the detached descendant remains in the
managed topology. The harness therefore reaches its outer timeout instead of
observing a normal launcher return. Both outcomes can be safe only when cleanup
is identity-bound and zero residue is proved before the diagnostic is consumed.

The startup-relative canary was ordered before the timeout cleanup trigger, so
it could never distinguish an escaped survivor from a descendant that was
later killed correctly. The timeout text alone is also insufficient: it could
represent slow startup, the wrong executable or mode, a real MPI hang, or an
incomplete cleanup. Substring matching is unsafe because `detach` is contained
in `detach-kill`.

## Solution

Keep the bounded timeout and use a post-cleanup one-shot gate:

1. Parse the diagnostic command list and bind the exact expected timeout,
   `test_process_control`, and current `detach` or `detach-kill` mode.
2. The inner managed runner calls its zero-residue assertion before raising.
3. The detached child validates a random lowercase-hex token, writes the exact
   armed record, and waits without writing a canary.
4. The escape PID evidence contains exactly one positive, no-longer-live PID.
5. Only then does the host create-new and fsync the exact release token. A
   survivor writes the canary after observing that gate; reject canaries both
   before publication and throughout the bounded observation window.
6. A fresh ordinary MPI smoke command succeeds only after the gate passes.

Continue to accept the existing returned-with-live-descendant path under the
same cleanup and postcondition requirements.

## Negative Matrix

Reject a wrong timeout duration, executable or exact mode, unrelated exception,
missing/wrong armed evidence, missing escape PID, surviving PID, pre/post-gate
canary, repeated release file, or unexpected launcher success. Do not solve the
issue by increasing the timeout or by killing a numeric PID without
starttime/token ownership.

## Validation

The local MPICH r63 validator passed 10/10 but did not model the real 4-second
versus 15-second ordering; r64 then failed W3 with `detached MPI descendant
wrote delayed canary for detach` and was released cleanly. The r65 production
matrix passes 15/15 and the actual C gate compiles with
`-Wall -Wextra -Werror` and passes 5/5 runtime cases. These remain local results;
a fresh exact r65 W3 is required before submission.

## Applicability

Use this pattern only for intentional process-containment probes whose runner
owns and monitors the complete launcher tree. It does not authorize accepting
ordinary test timeouts, weakening real upstream test failures, or touching
foreign processes.
