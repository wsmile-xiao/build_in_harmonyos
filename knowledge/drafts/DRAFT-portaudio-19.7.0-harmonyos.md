# DRAFT-portaudio-19.7.0-harmonyos - Configure feature probing and no-device QA

> **Contributor**: xuguowei | **Status**: VERIFIED DRAFT | **Updated**: 2026-08-19
> **Severity**: high | **Category**: autotools / pthread / audio-testing

## Implementation

The OHOS portability patch uses `AC_CHECK_FUNCS([pthread_cancel])` and the
generated `HAVE_PTHREAD_CANCEL` macro. It does not use an `__OHOS__` source
branch, so cancellation follows the target libc's actual POSIX link capability.

The package audit tracks 49 upstream targets: 30 `TESTS`, three `SELFTESTS`,
and the release's QA/example/loopback targets. Only `paqa_errs` is hardware
independent. The other 48 require an enabled host API, input/output hardware,
loopback, stable latency timing, or privileged host tools and are explicitly
deferred rather than counted as passed.

## Verification boundary

The consumer test validates the public API with `host_apis=0 devices=0`.
Official OHOS CI #27925 signed and ran `paqa_errs`; it reported `20 passed,
0 failed`. A hardware-enabled run should execute the remaining 48 targets with
their documented prerequisites.

## Source

- Package: `archives/p/portaudio/19.7.0`
- Issue: `OpenHarmonyPCDeveloper/BitFun#33`
- PR: `build_in_harmonyos!5739`
