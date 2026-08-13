# E320 draft - Preserve joinable thread teardown without `pthread_cancel`

> Status: DRAFT | Source: JACK 1.9.22 PR #3482, commit `98d26a683`
> Related: E085 and E127 document missing cancellation symbols. This draft
> covers the separate question of preserving joinable-thread lifecycle.

## Problem

When a target libc omits `pthread_cancel()` and `pthread_setcanceltype()`, a
package may compile after guarding those calls. That alone is insufficient for
a joinable worker thread. Replacing `pthread_cancel()` with a successful no-op
stub leaves the worker alive, while the owner still calls `pthread_join()` and
expects it to have exited.

The failure mode is a hang, a leaked worker, or teardown that races a live
thread. It is a runtime semantic defect, not merely a missing-symbol error.

## Applicable design

Use this only when the project already has a documented, reserved signal-based
exit mechanism or can safely add one:

1. Retain upstream `pthread_cancel()` behavior when the API is available.
2. In the fallback, install a `sigaction` handler before starting the joinable
   worker. The handler performs the project's minimal thread-exit action.
3. Send the reserved signal to that exact worker with `pthread_kill()`.
4. Join the same worker and update lifecycle state only after `pthread_join()`
   returns.
5. Do not block the reserved signal in global or control-path signal masks.

For JACK 1.9.22 the fallback uses the upstream Android-style `SIGUSR1` path:
`JackThreadCancel()` calls `pthread_kill(thread, SIGUSR1)`, the handler calls
`pthread_exit(0)`, and `Kill()`/`KillImp()` still call `pthread_join()`.
`0006-common-JackControlAPI-signal.patch` keeps `SIGUSR1` out of JACK's blocked
control signal set when `JACK_DISABLE_PTHREAD_CANCEL` is active.

## Verification

Verify the fallback as a lifecycle operation, not just a successful compile:

```text
start joinable worker
request fallback cancellation
pthread_join returns
worker state becomes idle
```

The project must also prove that the reserved signal is not used by another
component with incompatible process-wide semantics. If that cannot be shown,
use a project-native cooperative stop flag and wakeup mechanism instead.

## Do not do this

- Do not provide a no-op `pthread_cancel()` stub that returns success.
- Do not send a signal without installing an appropriate handler.
- Do not block the fallback signal in the application signal mask.
- Do not count a guarded compilation as proof that thread teardown works.
