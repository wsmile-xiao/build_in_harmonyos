# E318 Draft: validate fixed-target compilers without mixing target ABIs

> **Contributor**: xuguowei | **Status**: DRAFT | **Created**: 2026-08-12
> **Severity**: medium | **Category**: compiler/test adaptation

## Error surface

This pattern appears when adapting `chibicc/1.0.24.1` on an OHOS/armv8 worker:

```text
make: inaccessible or not found
can't create temporary file /tmp/sh*.tmp: Read-only file system
features.h: ... no expression
bits/alltypes.h: ... expected an expression
```

The package executable runs on armv8, while generated programs are x86-64. A compile-only gate may pass without proving generated executable behavior, and a naive worker-header merge may fail inside the wrong target ABI.

## Root cause

chibicc has separate host and generated-code architectures:

- the packaged compiler is an OHOS/armv8 executable;
- chibicc 1.0.24.1 unconditionally emits x86-64 code;
- upstream `make test` and `make test-stage2` link and execute generated x86-64 programs;
- OHOS/armv8 libc headers are not a substitute for x86-64 target headers.

The worker may also lack `make` and have a read-only `/tmp`. These are execution-environment constraints, not permission to rewrite headers or count blocked inputs as passing.

## Recommended handling

1. Build the host compiler with the Conan profile compiler and the upstream Makefile source set when `make` is unavailable.
2. Reuse the parent recipe's SHA256-verified source cache; do not download source again in `test_package`.
3. Validate exact source inventories before execution. For chibicc 1.0.24.1, require 980 `test/*.c` files and 13 stage2 compiler sources.
4. Keep ordinary public-driver fixtures that prove the package runs and emits non-empty assembly.
5. Never inject worker-architecture libc or dependency headers into a fixed-target compiler path.
6. Derive the source-owned compile subset and target-header blocker map from the pinned include graph.
7. Invoke every source-owned input and report its real terminal state.
8. Use version-locked XFAIL only for proven deterministic compiler gaps. Bind each entry to an exact name and diagnostic category.
9. Treat XPASS, diagnostic drift, unknown missing headers, and unknown failures as blocking.
10. Keep absent generated-test dependencies separate. The exact three Csmith inputs need `csmith.h` from another adaptation.
11. Report compile-stage and executable-stage denominators separately.
12. Add a matching native target environment when upstream tests generate another architecture.
13. In the native environment, require complete stage1/stage2 accounting and preserve every non-PASS result.
14. Require stage2 to contain all self-hosted compiler objects; label or reject any host-object fallback.

## Native runner design

For a fixed x86-64 target compiler, a useful native runner should:

- require Linux `x86_64` and glibc rather than silently accepting a different libc;
- copy the verified source to a disposable work tree;
- attempt all 980 stage1 programs and the driver suite;
- bootstrap stage2 from the exact 13 compiler sources;
- attempt all 980 stage2 programs and the driver suite;
- keep compile logs and per-executable output logs;
- write one result row per logical entry;
- classify `PASS`, `RUNTIME_FAIL`, `COMPILE_FAIL`, and `DEPENDENCY_BLOCKED` separately;
- fail if the inventory is incomplete, even when the measured pass rate is below 100%.

Clearing an unused Makefile link flag such as `-lcrypto` is acceptable only after confirming no compiled object references that library and documenting the harness adjustment. It must not change source or test bodies.

## Validation checklist

- packaged `bin/chibicc` exists, executes, and answers `--version`;
- four independent OHOS fixtures emit non-empty x86-64 assembly;
- source cache has exactly 980 test sources and 13 stage2 sources;
- source-owned inventory is exactly 607;
- target-header blocker map has exactly 1037 unique pairs;
- known XFAIL inventory has exactly 62 existing source names;
- XFAIL receives no PASS credit and XPASS blocks CI;
- the exact three Csmith inputs are separately guarded;
- no OHOS/armv8 libc headers enter x86-64 generated-code validation;
- native stage1 and stage2 both include the upstream driver suite;
- stage2 bootstrap proves all 13 self-hosted objects;
- native result rows total exactly 1962;
- pass and execution coverage use explicit denominators;
- result manifest hash is recorded.

## Evidence from PR #4710

### OHOS/armv8

CI #24498 built and signed the package, passed `4/4` ordinary fixtures, and reached the public-driver corpus. It measured:

- stage1: 584 PASS, 62 deterministic compiler failures, 331 target-header blockers, and 3 Csmith blockers;
- stage2 source boundary: 13 target-header blockers;
- complete compile-boundary inventory: 993 inputs.

The exact XFAIL/XPASS gate then passed in CI #24519 on head `ce913c9c2c`: `62/62 XFAIL`, `0 XPASS`, and `0 unexpected failures`. XFAIL remains non-PASS.

### Native glibc/x86-64

The previous executable count was `0/1962` because the available worker was armv8. The completed native run used QEMU 11.1.0 TCG, Linux 6.12.94, Ubuntu 24.04.4 LTS, GCC 13.3.0, and GNU Make 4.3.

No source or `test/*.c` body was changed. Stage2 bootstrapped from all `13/13` self-hosted objects without fallback.

| Stage | PASS | Runtime fail | Compile fail | Dependency blocked | Total |
| --- | ---: | ---: | ---: | ---: | ---: |
| stage1 | 962 | 9 | 7 | 3 | 981 |
| stage2 | 952 | 10 | 16 | 3 | 981 |
| **Total** | **1914** | **19** | **23** | **6** | **1962** |

The complete upstream pass rate is `1914/1962` (`97.55%`). Actual executable/driver coverage is `1933/1962` (`98.52%`). Both drivers passed. The per-case TSV has SHA256 `d27ac9551fdc05100efe55311a53111bd299776023bfc878bccf57c8906ee432`.

An Alpine/musl attempt was not used as final evidence because this fork hardcodes glibc header and linker layouts and failed during stage2 self-hosting. Repeating the test under matching glibc userspace is the correct environment fix; rewriting source headers would not be.

## Non-weakening rule

Do not:

- count XFAIL, target-header blocker, dependency blocker, compile failure, or runtime failure as PASS;
- accept a missing file solely because the message ends in `No such file or directory`;
- accept only an aggregate failure count without per-case identities;
- let XPASS or diagnostic drift pass silently;
- rewrite target libc or source headers to inflate compile counts;
- claim executable success from assembly-only validation;
- call a hybrid stage2 build fully self-hosted;
- combine a missing dependency or parent-recipe adaptation into the compiler knowledge PR.

The strongest statement for this package is now two-part: OHOS/armv8 package and exact compile-boundary gates pass; matching glibc/x86-64 execution accounts all 1962 upstream logical entries with a measured `97.55%` pass rate and explicit non-PASS outcomes.
