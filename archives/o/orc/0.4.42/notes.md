# orc 0.4.42 adaptation notes

## Scope

This package builds the core `orc-0.4` library from the official GStreamer
release archive. The first pass disables `orcc` tools, examples, benchmarks,
hotdoc documentation, the `orc-test` helper library, and upstream tests so the
OHOS package has a focused runtime-library surface.

## Test coverage

Upstream Meson registers 13 concrete tests when `tests`, `orc-test`, and
`tools` are enabled in a non-cross build: ten tests in `testsuite/meson.build`
and three generated `orcc` tests in `testsuite/orcc/meson.build`. Per-target
variants are added for runnable SIMD backends on matching CPU families. The
Conan package disables these upstream tests for cross-build packaging. The
added `test_package` builds and runs one C consumer test with six checks over
version query, program creation, program name round-trip, variable
registration, program compilation, and DSL parsing.

## Local validation

Local validation completed on Windows with MinGW GCC 8.1.0, Meson 1.11.2, and
Ninja 1.13.0 from a temporary venv under `E:\code\harmony\tmp`:

- Python syntax check passed for the main recipe and test recipe.
- `git diff --check` passed.
- Placeholder/secret-marker scan over `archives/o/orc` had 0 hits.
- Official source archive SHA256 verification:
  `7ec912ab59af3cc97874c456a56a8ae1eec520c385ec447e8a102b2bd122c90c`.
- Native Meson configure/build/install of static `liborc-0.4` passed with
  tools, examples, benchmarks, docs, `orc-test`, and upstream tests disabled.
  The Windows native precheck used `_WIN32_WINNT=0x0600` so MinGW declares SRW
  lock APIs; the OHOS path uses pthreads instead.
- Manual installed-library consumer compile/run of `test_package/test_orc.c`
  with `ORC_STATIC_COMPILATION` passed; local consumer checks passed 6/6.
- A fresh isolated Conan home completed native Windows x86_64 MinGW
  `conan create` for this recipe. Package build/install succeeded and the
  exact CMake test package passed CTest 1/1 in 0.32 seconds.
- A separate native upstream configuration enabled `orc-test`, `tests`, and
  `tools`. All 33 registered Meson tests ran: 32 passed and
  `mmx - orc:memcpy_speed` timed out at both 30 and 150 seconds. The timeout
  is not treated as a passing test.

Remaining limitation: this evidence is native Windows x86_64, not a completed
OpenHarmony runtime test run. The MMX performance-test timeout remains a
non-passing upstream result.
