# rt-app 1.0 adaptation notes

## Source and version

- Upstream: `https://github.com/scheduler-tools/rt-app`, tag `v1.0`
  (commit `a477fe226cbe3652a5d30a191fdf84ebbf744d25`).
- `conandata.yml` fetches the official GitHub tag tarball and pins its SHA256
  (`7562bd5f…0259f6`). No fork, no mirror, no CDN (R39).
- Version `1.0` is the upstream version for a first adaptation (R37). Any later
  fix against the same upstream tag must bump to `1.0.1`, `1.0.2`, … because the
  artifact repository cannot hold two recipe revisions of one version.
- The release archive ships no generated `configure`, only `autogen.sh`, so
  `build()` runs `autoreconf --install --force` before configuring.

## Build system and dependency notes

- Autotools (`AC_PROG_CC`, `AC_PROG_LIBTOOL`). Autoconf 2.71 reports
  `AC_PROG_LIBTOOL` and `AC_HEADER_STDC` as obsolete; both are warnings only and
  do not fail `autoreconf`.
- **The HarmonyOS worker ships only the autoconf half of the autotools stack.**
  `/data/service/hnp/bin` provides `autoreconf`/`autoconf`/`autom4te`
  (`/data/service/hnp/autoconf.org/autoconf_2.72`) but no `aclocal`, no
  `automake` and no `libtoolize`, so a bare `autoreconf --install --force`
  aborts with
  `Can't exec "aclocal": No such file or directory at .../Autom4te/FileUtils.pm`
  and `autoreconf: error: aclocal failed with exit status: 2` (CI build #67859,
  worker `OpenHarmonyPCDeveloper-CI-033`). `configure.ac` needs both halves
  (`AM_INIT_AUTOMAKE` + `AC_PROG_LIBTOOL`), so `build_requirements()` declares
  `automake/1.18` and `libtool/2.5.4` as `tool_requires` and `generate()` emits
  a `VirtualBuildEnv` so their `ACLOCAL`/`AUTOMAKE`/`LIBTOOLIZE` paths,
  `ACLOCAL_PATH` and relocatability fixups (`PERL5LIB`, `_lt_pkgdatadir`) reach
  the `conanbuild` environment. Same mechanism as `jool-modules-lts` 6.18.39,
  `jbig2enc` 0.32 and `quickfix` 1.15.1. autoconf/m4/perl are intentionally
  *not* declared: the SDK already provides them.
- `AC_CHECK_LIB([json-c], [json_object_from_file])` is satisfied by the
  `json-c/0.17` recipe from the artifact repository (verified published with
  `conan download json-c/0.17 -r=ohpcd --only-recipe`). `-lrt`, `-lm` and
  `-lpthread` resolve against the OHOS sysroot.
- The bundled `config.sub` (automake 1.16) **rejects** the `aarch64-linux-ohos`
  triplet that Conan derives for OHOS
  (`config.sub aarch64-linux-ohos` -> ``OS `ohos' not recognized``). The recipe
  therefore configures with `--host=aarch64-linux-gnu`, which canonicalizes to
  `aarch64-unknown-linux-gnu` and is accepted, while the toolchain keeps
  emitting `aarch64-linux-ohos` objects and linking against the OHOS sysroot.
- `--with-deadline` is intentionally left at its upstream default (`no`), which
  is what plain `./configure` does. That skips `libdl/` (the raw
  `sched_setattr` syscall shim); nothing is cropped relative to upstream's own
  default build.
- **HMDFS forbids the ``umask 077`` temporary directory (E011/E129).** Worker
  build trees live on HMDFS, which forces the setgid bit and ignores `chmod`,
  so autoconf's `(umask 077 && mktemp -d "./confXXXXXX")` produces a
  `drwx--S---` directory that not even its owner may write, and configure dies
  with `./config.status: line 818: ./confMOKcFd/subs1.awk: Permission denied`
  plus `could not setup config files machinery` (CI build #68375, worker
  `OpenHarmonyPCDeveloper-CI-019`). `build()` calls
  `_relax_autoreconf_tmpdir_umask()` on the `configure` that `autoreconf`
  generates, dropping the `(umask 077 && ` guard; configure copies that block
  verbatim into the `config.status` it writes, so both are fixed at once. This
  is a runtime replacement rather than a conandata patch because the tarball
  ships no `configure` (patches are applied before `autoreconf`) and the
  automake 1.18 line number drifts — same reason as `jbig2enc` 0.32. The
  helper is fail-closed: if the expected text is missing the build stops rather
  than shipping a recipe that only breaks on the worker.
- `make -j1`: HMDFS rejects libtool's jobserver FIFO (E074), so the recipe
  deliberately does not raise the job count.

## Porting patches

Three patches are registered in `conandata.yml`. None of them keys off a
platform macro such as `__OHOS__`; every change is portable C that is also valid
on glibc (R8).

1. `0001-define-bool-and-include-sched.patch` — `src/rt-app_types.h`
   - **Upstream bug**: `rt-app_parse_config.c` uses `TRUE`/`FALSE` (28 call
     sites) but nothing in the tree ever defines them, so tag `v1.0` **does not
     compile on any libc**. Verified: `gcc -fsyntax-only` on an unmodified
     Ubuntu glibc host fails with `‘TRUE’ undeclared`. The patch supplies the
     two guarded definitions in the shared header.
   - Adds `#include <sched.h>`. The file stores `cpu_set_t` in
     `cpuset_data_t` but only included `<pthread.h>`, which on glibc pulls the
     definition in transitively; the OHOS `pthread.h` only forward-declares
     `struct cpu_set_t` and never provides the typedef.
2. `0002-enable-gnu-source-for-cpuset.patch` — `src/rt-app_args.c`,
   `src/rt-app_utils.c`
   - The OHOS `sched.h` wraps `cpu_set_t` and the whole `CPU_*` macro family in
     `#ifdef _GNU_SOURCE` (lines 51–141). Only `rt-app.c` and
     `rt-app_parse_config.c` define `_GNU_SOURCE`, so the two files above failed
     with `unknown type name 'cpu_set_t'`. The patch defines `_GNU_SOURCE`
     before their system includes, matching the idiom upstream already uses in
     `rt-app.c`.
3. `0003-use-posix-sched-affinity-api.patch` — `src/rt-app.c`
   - musl-based OHOS libc exposes **no** `pthread_getaffinity_np`,
     `pthread_setaffinity_np` or `pthread_yield`
     (`grep -rn "getaffinity_np|setaffinity_np|pthread_yield" $OHOS_SYSROOT/usr/include`
     returns nothing). Replaced with POSIX `sched_getaffinity(0, …)`,
     `sched_setaffinity(0, …)` and `sched_yield()`. On Linux a `pid` of 0 means
     the calling thread, so `pthread_self()` semantics are preserved exactly, and
     the replacement also builds unchanged on glibc. The `perror()` strings were
     updated to match the new call names.

## Upstream defects observed (NOT fixed by this recipe)

These are pre-existing upstream bugs in tag `v1.0`. They are recorded here
because they shape how the tests are written; they are not regressions from the
HarmonyOS port.

- **Unbounded calibration.** With no `global.calibration` value, `main()` calls
  `calibrate_cpu_cycles()`, whose first method sleeps 1 s per trial for up to
  1000 trials (≈16 min) before it converges. The consumer test therefore presets
  `global.calibration` to a fixed ns-per-loop value so the run is fast and
  deterministic.
- **Global options must be nested.** Global settings are read from a `global`
  object (`rt-app_parse_config.c:972`), not from the document root; putting
  `calibration`/`duration` at the root silently falls back to defaults.
- **`lock_pages` is a boolean**, not an integer; `0` is rejected with
  `Invalid type for key lock_pages`.
- **No command-line options.** rt-app 1.0 only accepts `<taskset.json>`; every
  behaviour (duration, calibration, policy) is driven from the JSON document.

## Test strategy

rt-app has **no upstream test suite** — no `TESTS`, no `check_PROGRAMS`, no
`check-local`, no `tests/` directory, so `make check` runs zero cases and asserts
nothing. The audit evidence is recorded in `test_package/MANIFEST.yml`.

`test_package/run_tests.sh` therefore supplies 12 assertions, all of which
execute the *packaged* binary or a program built by the same cross toolchain
(R34):

| Case | Kind | What it asserts |
|------|------|-----------------|
| `CLI_Usage_NoArgs` | base | no argument prints `rt-app <taskset.json>` and exits 0 |
| `CLI_Usage_AbsentConfigFile` | base | absent config file falls back to the same usage text |
| `CONFIG_InvalidJson` | base | malformed JSON → `Error while parsing input JSON`, exit 2 |
| `CONFIG_InvalidKeyType` | base | wrong value type → `Invalid type for key period`, exit 2 |
| `RUN_WorkloadTerminates` | base | duration-bounded workload exits 0 |
| `RUN_PresetCalibrationHonoured` | base | `global.calibration` skips the ns-per-loop calibration |
| `RUN_PolicyApplied` | base | worker thread reports `SCHED_OTHER policy with priority 0` |
| `RUN_ResultLogHeader` | base | `rt-app-ThreadA-0.log` written with the expected header |
| `RUN_ResultRowsPresent` | base | result log holds at least one real timing measurement |
| `RUN_ResultRowsWellFormed` | base | every measurement row has the 11 expected columns |
| `OHOS_ArtifactIsAarch64ELF` | **OHOS** | the delivered binary is a 64-bit AArch64 ELF (ELF header parsed in plain C) |
| `OHOS_SchedulingApi` | **OHOS** | `cpu_set_t` + POSIX `sched_getaffinity`/`sched_setaffinity`/`sched_yield` work on target |

The two `OHOS_*` cases are the HarmonyOS-specific coverage: they pin down exactly
the surface the three porting patches rewired, so a future patch that reverts to
the glibc-only `pthread_*_np` calls would stop compiling and fail loudly.

### `CPU_ALLOC_SIZE` is not `sizeof(cpu_set_t)` (test-side defect, CI #68391)

`ohos_sched_test.c` originally did

```c
alloc_size = CPU_ALLOC_SIZE(cpu_count);
heap_set = CPU_ALLOC(cpu_count);
memcpy(heap_set, &current, alloc_size);
check(CPU_EQUAL(heap_set, &current), "...");
```

On OHOS/musl `CPU_ALLOC_SIZE(n)` is
`sizeof(long) * ceil(n / (8*sizeof(long)))` — **8 bytes** on aarch64 for any
device with up to 64 CPUs — while `CPU_EQUAL` is
`CPU_EQUAL_S(sizeof(cpu_set_t), ...)`, a **128-byte** `memcmp`
(`sysroot/usr/include/sched.h` lines 121-125). So only 8 bytes were copied into
an 8-byte allocation and the comparison then read 120 bytes past its end and
compared recycled heap. It passed on the emulated runner only because
`calloc` returned freshly zeroed pages; on real hardware build **#68391**
(worker `OpenHarmonyPCDeveloper-CI-033`) it reported
`not ok - a heap-allocated cpu_set_t compares equal to the mask`
(13 assertions, 12 passed, 1 failed), which also failed the two `OHOS_*` cases.

The check is now sound: `CPU_ALLOC()` is exercised on its own advertised size
and compared with `CPU_EQUAL_S(alloc_size, ...)`, and the full-mask comparison
runs through a buffer that really covers what `CPU_EQUAL` reads. The test also
dirties the allocator (fill/release 64 same-sized chunks) before the check, so
the assertion can no longer pass on zeroed pages alone and would catch a
reintroduction. Locally reproduced with the cross toolchain under qemu:
`CPU_EQUAL(heap_set, &current) -> NOT equal` before, `15 run, 15 passed` after.

## Verification notes

- Build verified with `conan create` against `-pr:h=ohos-aarch64-wsl
  -pr:b=ohos-aarch64-wsl`: the artifact is
  `ELF 64-bit LSB pie executable, ARM aarch64`.
- The workload case was executed on the aarch64 target and produced real
  measurements (239 rows in an unbounded run, 8 rows in the 3 s duration-bounded
  run), each row carrying `perf`/`run`/`period`/`start`/`end`/`rel_st`/`slack`.

## Local CI gate result (`ci/conan/build_and_test.sh`)

Run with `CI_BRANCH=feat/rt-app-1.0 CONAN_PROFILE=ohos-aarch64-wsl
CI_PACKAGES="archives/r/rt-app/1.0"`, exit code **0**, build summary
`Success: 1/1 (100%)`:

| Gate | Result | Note |
|------|--------|------|
| G0 | pass | |
| KC | pass | |
| JC | pass | `junk_check` runs in *incremental* scope (`git diff origin/main...HEAD`, 20 files), so only this PR's files are scanned |
| L0 | pass | all checks passed |
| L1 | pass | `test_package` executed, 12/12 assertions |
| L2 | **skip** (non-blocking) | see below |
| L4 | pass | patches clean |
| L5 | pass | `bin/` has content |

`L1e` (destructive negative test) confirmed the suite genuinely depends on the
package: moving `bin/` away makes the test fail, so it cannot pass hollowly.

**Why L2 is skipped, and why that is not a defect.** L2 probes
`rt-app --version` / `--help`. rt-app 1.0 accepts **no command-line options at
all** — its only argument is an optional `<taskset.json>` path, and passing an
unreadable path falls back to the usage text. There is no upstream `--version`
or `--help` flag to exercise. Adding one would mean changing the tool's CLI
contract beyond the scope of a platform port, so the gate's non-blocking `skip`
is accepted rather than papered over. The CLI surface is instead covered
deterministically by `CLI_Usage_NoArgs` and `CLI_Usage_AbsentConfigFile`, which
assert the real usage text and exit status.

Note for future runs: `build_and_test.sh` rewrites the working-tree
`conandata.yml` to inject a `gh-proxy.com` mirror fallback and leaves a
`conandata.yml.orig` behind. That rewrite must never be committed (R39 requires
the official source URL); restore the file and delete the `.orig` after a local
gate run.