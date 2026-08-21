# True-device Shadow CI report

- Package: `avr-libc/2.2.1`
- Device OS/arch: HarmonyOS/aarch64
- Final date: 2026-08-21
- Final result: pass

## Final run

```text
outer run:
  /storage/Users/currentUser/ohos-test-runs/
  codex-avr-libc-shadow-ci-r20-2240-requeued-20260821-160012-62802

shadow run:
  /storage/Users/currentUser/ohos-users/codex/avr-libc-2.2.1-2240-archive/
  ohpc-ci-shadow/runs/
  codex-avr-libc-shadow-ci-r20-2240-requeued-20260821-160012-62802

device commit: 55eacfea2a4f0f547f6778b093cfba469024858e
source tree:   c61928fec26ad367639afcdbc6ce9913651cab89
start:         2026-08-21 16:00:12 +0800
lock acquired: 2026-08-21 16:02:22 +0800 (waited 129 seconds)
end:           2026-08-21 16:51:41 +0800
exit code:     0
```

The global single-package lock was acquired before the build. The full recursive
AVR device/multilib build completed all 470 generated directories. Selected
upstream compile/link cases then passed:

```text
string/strcmp.c  ATmega328P  OK
stdlib/atoi-1.c  ATmega328P  OK
math/cos-01.c    ATmega328P  OK
3 files, Success
```

The final `test_package` output was:

```text
avr-libc consumer compile/link test passed for ATmega328P
```

Gate and package summary:

```text
G0_RESULT=pass
CI_PACKAGES received: archives/a/avr-libc/2.2.1
Found 1 package(s) to build
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
covered by both upstream compile/link cases and the Conan consumer.

## Iteration history

| Run | Result | Finding and correction |
|---|---|---|
| r17 | timeout | Single-threaded 470-directory build exceeded one hour; build parallelism changed to `-j4`. |
| r18 | fail | Full build completed, but upstream default `atmega128` selected avr51, absent from the stage-1 bootstrap GCC multilibs. |
| r19 | fail | ATmega328P upstream tests passed and packaging completed; consumer incorrectly required `sin` to be a strong `T` symbol. |
| r20 | pass | Consumer validates `memcpy=T`, `strlen=T`, and the expected weak `sin=W`; all package gates completed. |

## Coverage boundary

The upstream tree contains 462 simulator test sources. Three representative tests
were compiled and linked. Full simulator execution was not attempted because
`avrtest` and `simulavr` are not packaged dependencies. The report therefore makes
no claim that all 462 tests executed or passed.
