# cthreadpool 0.0-git20231218.4eb5a69 adaptation notes

Upstream ships no build system at all: the library is exactly two files
(`thpool.c` + `thpool.h`), plus `example.c` and a shell-driven test suite
under `tests/`. The recipe therefore compiles `thpool.c` directly with the
Conan-profile compiler (always `-fPIC`, so the same object feeds both the
static archive and the shared object) and packages both `libthpool.a` and
`libthpool.so` plus the public header. There is deliberately no `make`,
`cmake`, or `configure` indirection to port.

## Compatibility audit (pinned commit 4eb5a69, 2023-12-18)

- `thpool.c` is POSIX C plus pthreads only: `pthread_create`/`pthread_detach`,
  mutexes, condition variables, `pthread_kill` with a `SIGUSR1`/`sigaction`
  handler for pause/resume. `SA_ONSTACK` is declared thanks to the upstream
  `_POSIX_C_SOURCE 200809L` guard (upstream PR #128); no patch needed.
- Thread naming uses `prctl(PR_SET_NAME, ...)` under `#if defined(__linux__)`
  with ignored return value, so even an OHOS kernel without that prctl
  operation cannot fail the build or the tests. No musl-incompatible or
  glibc-only symbols were found (`sleep`, `sigaction`, `pthread_kill` are all
  in the platform C library).
- Upstream never calls `pthread_cancel`, so the OHOS gap that required a
  fallback macro in clthreads does not apply here.

## Test inventory

Upstream `tests/` holds 6 test programs driven by shell scripts (no test
runner with countable cases; counts below are driver invocations):

| Driver | Invocations | Needs on OHOS |
|--------|-------------|---------------|
| `threadpool.sh` (`conc_increment`: 100/4, 100/1000, 100000/1000) | 3 | only cc + sh |
| `api.sh` (`api.c`: working-thread counters) | 1 | only cc + sh |
| `wait.sh` (`wait.c`: per-job and pool-wide waits) | 7 | `/usr/bin/time` + python threshold checks |
| `pause_resume.sh` (`pause_resume.c`: ~7 s pause/resume) | 1 | only cc + sh |
| `heap_stack_garbage.sh` (`nonzero_heap_stack.c`) | 1 | `timeout(1)` |
| `memleaks.sh` (`no_work.c` under valgrind) | 9 | valgrind |

The recipe `build()` runs the portable subset with the exact upstream
compile line (`cc + thpool.c + -D THPOOL_DEBUG + -pthread`): the example
smoke test, the API test, all three `conc_increment` mass additions with
output comparison, two functional `wait.c` runs (timing thresholds are
host-calibrated and therefore asserted only as successful completion, not
as elapsed-time bounds), `pause_resume`, `no_work`, and
`nonzero_heap_stack` (runs to completion directly; no `timeout` wrapper).
The 9 valgrind leak cases from `memleaks.sh` are excluded because valgrind
is not available on OHOS; the same `no_work` binary still runs as a
create/destroy smoke test.

The installed-package layer (`test_package/`) adds two consumers that link
the packaged library and verify behaviour with counted assertions:
`test_basic` (200 queued increments, exact sum, zero working threads after
`thpool_wait`) and `test_pause_wait` (no progress while paused, exact sum
after resume, clean destroy).

## Verification status

- Local (Windows worker): source tarball downloaded from the official GitHub
  repository, SHA256 verified; recipe files written but `conan create` is
  intentionally not run here (per task rules, compilation happens on the
  HarmonyOS PC device via HMBS preflight).
- Device evidence (conan create, upstream suite, test_package): pending HMBS
  preflight; results will be recorded here and in `.hmbs/pr-body.md` once
  the structured logs return.
