# j4-dmenu-desktop 3.2 HarmonyOS PC adaptation

## Environment

- Target: HarmonyOS PC, aarch64, OHOS 6.0 profile
- Compiler: clang/clang++ 15.0.4 with libc++
- Build system: Meson 1.11.1 + Ninja

## Adaptation

The upstream project is portable C++17 and its inotify implementation builds
on HarmonyOS PC.  No upstream source patch is needed.

Three packaging details are handled by the recipe:

1. `spdlog/1.17.0` requires `fmt/12.2.0`; both are declared explicitly.
2. The registry packages expose nested include directories.  In particular,
   `include/spdlog` shadows `<fmt/ranges.h>` with spdlog's forwarding header.
   The recipe narrows dependency metadata to each public `include` root before
   generating `.pc` files.
3. Meson is given the device `llvm-ar`, and compiler temporaries are placed in
   the writable build directory instead of the read-only system `/tmp`.
   The override is applied around the actual Meson configure, build, test, and
   install calls so it is not lost behind Conan's generated build environment.

Shell-completion regeneration is disabled because the release archive already
contains generated completions and the generator is not a target dependency.

## Tests

- Upstream Catch2 unit test executable: `j4-dmenu-tests`.
- Upstream pytest system suite: `tests/system_tests/system_test.py`.
- Consumer smoke test: installed command reports version/help and executes a
  deterministic `.desktop` entry through a dmenu-compatible selector.

Device results: Catch2 reported 73 passed and 6 skipped (256 assertions
passed); pytest reported 10 passed and 7 skipped.  The Catch2 skips are fixture
cases that hard-code the read-only system `/tmp`; the pytest skips are upstream
terminal-emulator parametrizations.  Both Meson suites completed with zero
failures.  A final clean-cache `conan create` also passed the consumer
`test_package`; its complete summary is in `reports/test-report.md`.

The latest `origin/main` CI build script also completed with a 1/1 package
pass rate. L0, L1, L4 and L5 passed. L2's raw-binary smoke check was skipped
because it does not load Conan's dynamic-library environment; the consumer
test covers the same version/help checks under `VirtualRunEnv` and passed.

## Knowledge extension

The reusable failure pattern is recorded as the paired draft
`knowledge/drafts/E543-draft-B715.{kv,md}`.  A four-scope duplicate search found
nearby entries E133, E217 and E348, but none covers PkgConfigDeps exporting a
nested include root that shadows another dependency's public header.  The
machine-readable result is stored in `reports/knowledge-dedup-result.json`.

---

**编译结束**: 2026-09-24 18:45
**最终状态**: built
