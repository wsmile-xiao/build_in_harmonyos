# OHOS native compressed input pipe lifetime

## Error signature

CaDiCaL's `parcompwrite` API test intermittently failed while multiple threads read gzip command output through `popen()`:

```text
API: 15 ok, 1 failed
```

The failure disappeared and returned across runs even though the solver result was correct.

## Root cause

OHOS native `popen()`, `fread()`, and `pclose()` usage was not safe when multiple threads owned compressed input pipes concurrently. Protecting only pipe creation left the subsequent reads and teardown exposed to the same race.

## Fix

Guard the complete read-pipe lifecycle with one recursive mutex:

1. lock before `popen()`;
2. keep the lock through every `fread()`;
3. call `pclose()` while still locked;
4. unlock on both successful and failed close paths.

The guard is platform independent. A recursive mutex allows the same thread to own overlapping read pipes, while different threads serialize compressed pipe creation, reads, and teardown. Write-mode pipes use a separate upstream path and must not share this lock.

## Validation evidence

A 100-thread probe produced:

```text
no serialization:                 69 failures
serialize popen creation only:    10 failures
serialize popen through pclose:    0 failures
```

The complete-lifetime implementation then passed the CaDiCaL r10 OHOS single-package shadow CI:

```text
API: 16 ok, 0 failed
Build Summary: Total: 1 / Success: 1 / Failed: 0
```

## Notes

Use the lock scope as the boundary for judging similar failures. A lower failure count after locking only `popen()` is useful evidence, but it is not a fix because it leaves later pipe operations unprotected.
