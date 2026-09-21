# DRAFT-cmake-harmonyos-system-name-soname - Explicit SONAME flags and runtime LD_LIBRARY_PATH for Conan os=OHOS CMake shared libraries

> **Contributor**: GoliWie | **Status**: VERIFIED DRAFT | **Updated**: 2026-09-19
> **Severity**: medium | **Category**: cmake / shared-library / conan platform mapping / OHOS toolchain
> **Second independent hit**: first was `expat/2.8.2.1.1` (issue #1912, HMDFS symlink-denial trigger); this entry is the `kcolorpicker/0.3.1` hit via the plain CMake-consumer route (no Qt platform patch involved).

## Usage

Use this pattern when a Conan recipe on HarmonyOS PC (`os=OHOS`) builds a CMake
shared library and either:

1. upstream tests / ctest executables fail at startup with
   `Error loading shared library lib*.so: ... symbol not found` although the
   link step succeeded, or
2. the CI SONAME gate reports a missing `DT_SONAME` /
   `IMPORTED_NO_SONAME TRUE` in the exported CMake targets.

## Scope

- Any CMake shared-library project driven by the OHOS-adapted conan profile
  (`os=OHOS`), independent of Qt or any other framework.
- Both failure surfaces caused by the same root cause: missing runtime rpath
  rules (test phase) and missing SONAME flag (package/downstream phase).

This is not a fix for a broken compiler or missing dependencies. Apply it only
after confirming CMake printed `System is unknown to cmake, create:
Platform/HarmonyOS` during configure.

## Symptom

During CMake configure the log repeatedly shows:

```text
System is unknown to cmake, create:
Platform/HarmonyOS to use this system, please post your config file on discourse.cmake.org so it can be added to cmake
```

Downstream symptoms differ by phase:

- test phase: freshly linked test executables fail with
  `Error loading shared library libQt6*.so.6 / lib<name>.so` (the link line
  contains no `-rpath`/`-rpath-link` at all);
- package/gate phase: the produced `.so` has no `DT_SONAME`, the exported
  targets file carries `IMPORTED_NO_SONAME TRUE`, and downstream `DT_NEEDED`
  records the absolute Conan cache path (non-relocatable).

## Root Cause

The OHOS-adapted conan maps `os=OHOS` to `CMAKE_SYSTEM_NAME=HarmonyOS`
(documented in the profile itself, `ci/conan/profiles/ohos-aarch64`). The
device CMake 4.1.2 ships `Modules/Platform/OHOS.cmake` (which only does
`include(Platform/Linux)`) but no `Modules/Platform/HarmonyOS.cmake`. The
platform lookup fails, `Platform/Linux.cmake` never loads, and the variables
defined there — `CMAKE_SHARED_LIBRARY_SONAME_{C,CXX}_FLAG` and the rpath
rules — stay undefined. Consequences:

1. no `-Wl,-soname` on the shared-library link line and no rpath machinery at
   all (CMake silently drops `CMAKE_BUILD_RPATH`);
2. conan's aggregated build env does not propagate into `ctest`, so the
   build-tree test executables cannot resolve their `DT_NEEDED` libraries.

## Implementation

Keep SONAME emission enabled and disable versioned names/symlinks, then inject
the test-time library path explicitly:

```python
# SONAME (build semantics layer)
tc.cache_variables["CMAKE_PLATFORM_NO_VERSIONED_SONAME"] = "ON"
tc.cache_variables["CMAKE_SHARED_LIBRARY_SONAME_C_FLAG"] = "-Wl,-soname,"
tc.cache_variables["CMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG"] = "-Wl,-soname,"

# runtime closure for build-tree test executables (ctest phase)
test_env = Environment()
test_env.prepend_path("LD_LIBRARY_PATH", os.path.join(self.build_folder, "lib"))
test_env.prepend_path(
    "LD_LIBRARY_PATH",
    os.path.join(self.dependencies["<dep>"].package_folder, "lib"))
with test_env.vars(self).apply():
    self.run("ctest --output-on-failure -j1", cwd=self.build_folder)
```

This produces a single unversioned real `lib<name>.so` whose ELF carries
`SONAME lib<name>.so`, so downstream `DT_NEEDED` records a relocatable SONAME
instead of the Conan cache path. Do not bake rpath into installed artifacts:
post-install ELF edits require the E077 re-sign flow anyway.

An alternative (honestly unverified) fallback is to force
`CMAKE_SYSTEM_NAME=OHOS` after the Conan toolchain so the shipped
`Platform/OHOS.cmake` loads `Platform/Linux` natively; probe the toolchain
override order and semantics before relying on it.

## Forbidden Approaches

- Do not remove SONAME emission completely (`NO_SONAME`, empty soname flag):
  downstream `DT_NEEDED` captures the absolute Conan cache path and breaks on
  cache cleanup, revision change, or a different machine (proven by
  expat #1912).
- Do not delete or rename versioned symlinks in `package()`: the failure
  already happened at build/gate time; post-install cleanup cannot fix it.
- Do not rely on implicit loader resolution (default search paths, aggregated
  conan env inheritance into ctest) — the same recipe may link "successfully"
  on one worker and fail at runtime on another.
- Do not claim success from compilation alone; verify `DT_SONAME`, `DT_NEEDED`
  and a real test run.

## Verification

1. Confirm the missing platform module:
   `ls .../share/cmake-4.1/Modules/Platform | grep -i harmonyos` (empty) and
   the conan mapping: `grep -n HarmonyOS ci/conan/profiles/ohos-aarch64`.
2. Minimal shared-library probe, twice: without the fix flags
   `llvm-objdump -p libfoo.so | grep -c SONAME` must be 0; with
   `CMAKE_PLATFORM_NO_VERSIONED_SONAME=ON` plus the explicit soname flags it
   must be 1.
3. `llvm-objdump -p libX.so | grep DT_NEEDED` — no absolute Conan cache paths.
4. Run the upstream tests / ctest with the explicit `LD_LIBRARY_PATH`
   injection and require a real pass.
5. Run the CI negative-dependency test (move `lib/`+`include/` away) to prove
   the consumer genuinely depends on the packaged artifact.

## Validated Example

`kcolorpicker/0.3.1` (archives/k/kcolorpicker/0.3.1) hit both surfaces during
its first candidate: rounds 1-2 failed at test startup (no rpath), round 3
failed the CI SONAME gate, round 4 passed the full authoritative CI with
`SONAME [libkColorPicker.so]`, relocatable `DT_NEEDED` entries, a valid
`.codesign` section after the E077 re-sign flow, upstream `ColorButtonTest`
1/1 passed under `QT_QPA_PLATFORM=offscreen`, and a real
`find_package(kColorPicker-Qt6 0.3.1 REQUIRED)` + `kColorPicker::kColorPicker`
consumer test.

Related drafts: `DRAFT-expat-cmake-soname-1912` (first hit, HMDFS symlink
trigger), `DRAFT-openjpeg2-hmdfs-versioned-soname`, `E135` (dynamic loader
error family).
