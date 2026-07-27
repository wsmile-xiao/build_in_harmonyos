# E240 - Capability Split for macOS CoreGraphics Display CLIs on OHOS

## Symptom

A small upstream display utility builds cleanly only on macOS because it directly
includes Apple frameworks such as `ApplicationServices` and uses CoreGraphics
display APIs for current-mode query, mode listing, and physical mode changes.

When such a tool is adapted to OHOS, the public native API may only cover part
of the original CLI contract. For `screenresolution` 1.6, the useful OHOS C API
surface is:

```text
OH_NativeDisplayManager_GetDefaultDisplayWidth
OH_NativeDisplayManager_GetDefaultDisplayHeight
OH_NativeDisplayManager_GetDefaultDisplayRefreshRate
```

Those APIs can back `screenresolution get`, but they do not provide the same
full mode list and physical mode setter contract as the upstream CoreGraphics
implementation.

## Root Cause

The upstream program is not merely missing a build flag. Its feature model is
tied to a platform framework that exposes display mode enumeration and mutation.
OHOS NativeDisplayManager exposes enough public C API for read-only default
display metrics, but not enough for feature-equivalent `list` and `set` support
in this port.

## Fix

Split the CLI by real target capability:

1. Keep macOS on the upstream CoreGraphics backend.
2. Add an OHOS backend for `-version` and `get` using NativeDisplayManager.
3. Make `list` and `set` return non-zero with explicit unsupported diagnostics.
4. Add test-package assertions for both successful read-only behavior and
   negative unsupported behavior.

For `screenresolution` 1.6, the OHOS tests require:

```text
screenresolution version 1.6
Display 0: <width>x<height>x32@<refresh>
list is not supported on OHOS NativeDisplayManager backend
set is not supported on OHOS NativeDisplayManager backend
```

## Verification

Run the single package on a true OHOS PC target:

```sh
CI_PACKAGES="archives/s/screenresolution/1.6" zsh ci/conan/build_and_test.sh
```

The package should build only the target archive, run `test_package`, and report
`L0/L1/L4/L5=pass`. A generic `--version/--help` smoke check may remain a
documented non-blocking skip if the upstream CLI only supports `-version`.

## Path B Rationale

This is a Path B style adaptation because the work documents and enforces a
platform capability boundary rather than pretending the target API is fully
equivalent. The important part is that unsupported destructive or mode-changing
commands fail clearly and are covered by tests.
