# DRAFT-libsndfile-1.2.2-harmonyos - CMakeAutoGen and focused CTest validation on OHOS

> **Contributor**: xuguowei | **Status**: VERIFIED DRAFT | **Updated**: 2026-08-19
> **Severity**: medium | **Category**: cmake / ctest / OHOS

## Scope

Use this entry for `libsndfile/1.2.2` Conan builds on HarmonyOS PC when Conan's
multi-value `CMAKE_MODULE_PATH` interacts with the upstream CMakeAutoGen helper,
or when the complete upstream test matrix cannot be used as a deterministic
cross-device gate.

## Root Cause

Conan's generated CMake toolchain can expose `CMAKE_MODULE_PATH` as a list.
The upstream CMake helper formed the script path by appending a filename to
the list variable, producing an invalid path. The portability patch resolves
the helper relative to `CMAKE_CURRENT_LIST_DIR`, which is stable regardless of
the number of module-path entries.

The 1.2.2 source declares 143 CTest cases. The OHOS recipe intentionally runs
12 deterministic core cases covering file I/O, metadata, conversion, channel,
checksum, and virtual I/O behavior. Tests requiring optional external codecs,
pipe/stdio behavior, large format matrices, or host-specific facilities are
recorded as deferred rather than silently counted as passed.

## Implementation

- Apply `0003-fix-cmake-autogen-module-path.patch` before configuring.
- Keep `BUILD_PROGRAMS`, `BUILD_EXAMPLES`, and `BUILD_REGTEST` disabled for the
  package artifact; enable CTest only for the static build's focused gate.
- On OHOS, sign each selected test ELF before execution and verify exactly one
  `.codesign` section.
- Run the consumer `test_package` WAV/PCM write-read loop independently of the
  upstream CTest selection.

## Verification

The HarmonyOS shadow run passed the selected upstream subset (12/12) and the
consumer test (1/1). A clean Conan create also passed locally. The remaining
130 upstream declarations are documented in the package test inventory with
technical reasons for deferral; they are not represented as successful tests.

## Source

- Package: `archives/l/libsndfile/1.2.2`
- Issue: `OpenHarmonyPCDeveloper/BitFun#31`
- PR: `build_in_harmonyos!5578`
