# True-device Shadow CI report

- Package: `avr-libc/2.2.1`
- Device OS/arch: HarmonyOS/aarch64
- Final date: 2026-08-21
- Final result: pass

## Final run

```text
outer run:
  /storage/Users/currentUser/ohos-test-runs/
  codex-avr-libc-shadow-ci-r25-2240-resume-cache-20260821-200845-55576

shadow workspace:
  /storage/Users/currentUser/ohos-users/codex/avr-libc-2.2.1-2240-archive/
  ohpc-ci-shadow/runs/
  codex-avr-libc-shadow-ci-r24-2240-full-409-20260821-190344-19933

device commit: 6b817115bf6e48d28dc980437357bdf034aff66b
source tree:   e1efbb101173337ffd4ebdaa8df2a8811430cfb9
start:         2026-08-21 20:08:48 +0800
lock acquired: 2026-08-21 20:13:27 +0800 (waited 279 seconds)
end:           2026-08-21 21:03:12 +0800
exit code:     0
```

The global single-package lock was acquired before the build. Run r25 reused the
verified source cache from the cold-cache r24 attempt, but rebuilt the full 470
generated AVR device/multilib directories, reran all eligible upstream sources,
installed and packaged the sysroot, and executed the Conan consumer.

Upstream compile/link result:

```text
Done.  Number of operated files: 409
Success.
```

This covers all 406 C and 3 assembly sources that the C-only bootstrap toolchain
can compile. The 409/409 executed-source pass rate is 100%. The overall source
compile/link coverage is 409/462, or 88.53%.

The final `test_package` output was:

```text
avr-libc consumer compile/link test passed for ATmega328P
```

Final metadata and package summary:

```text
G0_RESULT=pass
L0_RESULT=pass: all checks passed
L1_RESULT=pass: test_package executed
L2_RESULT=skip: avr-man version/help failed
L4_RESULT=pass: no patches
L5_RESULT=pass: bin/ has content

Build Summary
Total: 1
Success: 1
Failed: 0
```

L2 is a non-blocking probe of `avr-man`. This documentation helper is installed in
`bin` but does not implement `--version` or `--help`; documentation generation is
disabled and it is not the primary package surface. The delivered AVR sysroot was
covered by the complete eligible upstream compile/link set and the Conan consumer.

## Iteration history

| Run | Result | Finding and correction |
|---|---|---|
| r17 | timeout | Single-threaded 470-directory build exceeded one hour; build parallelism changed to `-j4`. |
| r18 | fail | Full build completed, but upstream default `atmega128` selected avr51, absent from the stage-1 bootstrap GCC multilibs. |
| r19 | fail | ATmega328P upstream tests passed and packaging completed; consumer incorrectly required `sin` to be a strong `T` symbol. |
| r20 | pass | Representative 3/3 upstream checks, consumer and all package gates passed. |
| r21 | helper fail | A supplemental helper used `set -u`; Conan's optional `LDFLAGS` was unset. No library test ran. |
| r22 | 334/338 | The upstream default list on ATmega328P failed only four allocator sources whose source explicitly supports ATmega128 or AT90S8515. |
| r23 | 409/409 | All eligible C/assembly sources passed on AT90S8515; stderr was empty. |
| r24 | timeout after tests | Cold-cache full build and 409/409 tests passed; a roughly 12-minute source download caused the 3600-second limit to fire during `make install`. |
| r25 | pass | Reused only r24's verified source cache; full rebuild, 409/409 tests, install, package, consumer and gates passed in 49 minutes 45 seconds after lock acquisition. |

## Coverage boundary

The upstream tree contains 462 simulator sources: 406 C, 53 C++ and 3 assembly.
All 409 C/assembly sources were compiled and linked. The 53 C++ sources were not
compiled because the independently adapted stage-1 `avr-gcc-bootstrap` package
contains neither `avr-g++` nor `cc1plus`. Full AVR machine-code execution was not
run because `avrtest` and `simulavr` are not packaged dependencies. These are
explicit dependency blockers rather than failed avr-libc tests.
