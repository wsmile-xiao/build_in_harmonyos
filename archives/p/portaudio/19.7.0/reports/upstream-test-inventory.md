# Upstream test inventory

PortAudio 19.7.0's Autotools `Makefile.in` declares 30 programs in `TESTS` and
three programs in `SELFTESTS`: `paqa_devs`, `paqa_errs`, and `paqa_latency`.
The source archive contains 47 files in `test/`, 16 files in `examples/`, and
additional loopback QA sources.

## Upstream tests in the device gate

The recipe builds `paqa_errs` for OHOS even when Conan classifies the build as a
cross build, packages it under `tests/`, and runs it from `test_package` after
HarmonyOS signing. Official CI #27925 recorded:

```text
QA Report: 20 passed, 0 failed.
```

This is one selected upstream executable with 20/20 assertions passing. It is
kept outside `bin/` because it is package-validation material, not an installed
user command; consequently the generic L2 command gate remains inapplicable.

## Deferred tests

The other 48 inventoried upstream targets and examples open streams, measure
latency, record audio,
play generated signals, exercise underflow/overflow, or require a physical
loopback path. The OHOS package intentionally has no ALSA, JACK, OSS, or ASIHPI
backend, and the device test environment provides no controlled audio fixture.
Those cases are therefore not meaningful in this single-package gate and are
not modified or weakened.

## Consumer coverage

The explicit test package also provides deterministic no-hardware coverage of
the exported C API and package metadata. Both it and `paqa_errs` execute in the
same Conan test phase; the consumer remains subject to shadow CI's destructive
R34 dependency test.
