# libogg 1.3.6.2 adaptation notes

## Scope

This Path A candidate keeps the official Xiph 1.3.6 release archive (same
tarball and SHA-256 as the merged `1.3.6` / `1.3.6.1` recipes) and carries no
third-party Conan dependency. Per the version policy (first adaptation uses
the upstream version, adaptation fixes add a suffix), the recipe version is
`1.3.6.2`: upstream `1.3.6` plus the second adaptation fix. The fix itself is
test-evidence only: HMBS machine-evidence markers plus per-stage `CHECK`
output in the installed-package consumer. No source, build-system, patch, or
linkage change versus `1.3.6.1`.

## Source

- URL: `https://downloads.xiph.org/releases/ogg/libogg-1.3.6.tar.xz`
- SHA-256: `5c8253428e181840cd20d41f3ca16557a9cc04bad4a3d04cce84808677fa1061`
  (matches the checksum published on the xiph.org downloads page for
  `libogg-1.3.6.tar.xz`)
- Upstream tag: `v1.3.6` (`https://github.com/xiph/ogg`), release 2025-06-16
- Size: 439,952 bytes (same tarball audited for `1.3.6` / `1.3.6.1`)

The CMake route is kept, so no source patch is carried (the historical
`config.guess` / `config.sub` patches apply only to the old Autotools route).

## Test accounting

Official `CMakeLists.txt` (audited against upstream tag `v1.3.6`) registers
exactly two independent entries under `if(BUILD_TESTING)`: `test_bitwise`
from `src/bitwise.c` (`_V_SELFTEST`) and `test_framing` from `src/framing.c`
(`_V_SELFTEST`). There is no `enable_testing()` / `include(CTest)` call and
no `tests/` directory, so a plain CTest invocation finds zero entries.
Reusing E249, the recipe executes the two built official programs directly
and requires both process results instead of accepting an empty CTest run;
the run is reported with an `HMBS_UPSTREAM_TEST_RESULT` machine-evidence
marker (`discovered=2/executed=2`).

The Conan test package adds one installed-package integration flow that
encodes a packet, flushes it to a page, decodes it back, and verifies the
recovered bytes. The consumer now prints one `CHECK n OK` line per stage (4
stages) and exits non-zero at the first failing stage, so a zero exit plus
the four log lines proves the flow without relying on exit-0-alone. The four
stages share one process fate and are not split into cases, so the logical
total stays two upstream entries plus one integration flow
(`HMBS_TEST_PACKAGE_RESULT` `discovered=1/passedCount=1`). Shared and static
repetitions do not increase these totals.

## Changes versus 1.3.6.1

- Recipe version `1.3.6.1` -> `1.3.6.2`; `conandata.yml` source key follows.
  Same official URL and SHA-256 (no re-download risk, no mirror added).
- `build()` emits `HMBS_UPSTREAM_TEST_RESULT` (passed/failed with real
  executed counts); a failing official program now fails the marker first
  and then re-raises, so a red run can never look green. The marker is
  emitted dual-channel (stdout + conan log) and persisted to
  `build_folder/hmbs_upstream.json`, shipped into `res/` by `package()`,
  and re-emitted by `test_package` on every run so a cached
  `build()` (`Already installed!`) still satisfies the evidence gate;
  a missing persisted file only warns, never fakes a result.
- `test_package/test_package.c` prints per-stage `CHECK n OK` lines with an
  early non-zero exit per stage (exit-0-alone hardening, log stays non-empty
  and stage-attributable).
- `test_package/conanfile.py` emits `HMBS_TEST_PACKAGE_RESULT`
  (`discovered=1/passedCount=1` for the single integration flow) after the
  consumer really runs under the `conanrun` environment.
- `test_package/MANIFEST.yml` records the upstream audit
  (`upstream_tests_exist: true` with the `add_test` scan result).
- OHOS ELF self-signing and the `libogg.so` SONAME补签流程 are unchanged
  from `1.3.6.1` (downstream `DT_NEEDED` absolute-path hazard documented
  there still applies: fontconfig / poppler / tbb precedent).
- True-machine hardening (2026-09-13 preflight `compile` failure:
  `CMAKE_C_COMPILER: /data/service/hnp/bin/clang` broken +
  `[readonly_tmp]` /tmp read-only): `generate()`/`build()` in both the
  main recipe and `test_package` now force the Ninja generator
  (`tc.generator = "Ninja"`, `CMAKE_MAKE_PROGRAM` resolved via
  `HMBS_NINJA` / `user.hmbs:ninja_path` / fixed path / `PATH`, E346) and
  redirect `TMPDIR`/`TMP`/`TEMP` to the HMBS task-private tmp or
  `<build_folder>/hmbs-tmp` (E002, temp root only, no test skipped);
  signing/chmod steps tolerate `HMBS_CAP_CHMOD=0` and tool lookup prefers
  an existing absolute path with `PATH` fallback.
- Second preflight (same `cmake.configure()` compiler-ID failure with
  Ninja + writable TMPDIR already applied, mirroring the critnib/1.1
  journey) forced a different strategy: non-Windows builds now bypass
  CMake `try_compile` probes entirely (Exp1, apply) and compile with the
  validated profile compiler directly. Compiler selection reuses the
  m1ddc rule (Exp2, adapt: conf absolute path only when usable, else
  `clang` / fixed HNP path / `cc` / `$CC` fallback + smoke test first).
  Library TUs, `_V_SELFTEST` harnesses, include layout, SONAME scheme
  (`configure.ac` parsed at build time: SOVERSION 0, LIB 0.8.6) and
  installed interfaces (`ogg.pc`, `OggConfig.cmake`, `OggTargets.cmake`
  with `Ogg::ogg`, `pkg_config_name=ogg` for PkgConfigDeps downstream
  like oggz) mirror the upstream CMake route; no upstream source or
  assertion changed. Windows keeps the legacy CMake route untouched.
  Falsifiability: build runs an exit-1 stub negative control through the
  same runner, and test_package requires exit 0 plus all four `CHECK OK`
  lines.

## Current boundary

- The Windows shared import-library observation is inherited unchanged from
  `1.3.6.1` (upstream CMake names the import library `ogg.dll` while
  installing `libogg.dll`); it is a Windows-only metadata observation and
  establishes no OpenHarmony result.
- HMBS real-machine preflight (conan create shared + static on HarmonyOS
  aarch64) is pending: this round delivers the uncommitted work tree only,
  and the pass counts above become real numbers once the preflight log
  returns. CI and publication are not claimed.
