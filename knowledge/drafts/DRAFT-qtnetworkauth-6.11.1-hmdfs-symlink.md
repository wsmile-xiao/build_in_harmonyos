# DRAFT-qtnetworkauth-6.11.1-hmdfs-symlink - Materialize CMake symlink rules on HMDFS

> **Contributor**: AtomCode (GLM-5.2) | **Status**: DRAFT | **Updated**: 2026-09-22
> **Severity**: high | **Category**: hmdfs / qt6 / linking

## Problem

On the HarmonyOS PC device, HMDFS rejects symbolic links. When a Qt6 shared
module links `libQt6NetworkAuth.so`, CMake's `cmake_symlink_library` tries to
create `libQt6NetworkAuth.so -> libQt6NetworkAuth.so.6 -> libQt6NetworkAuth.so.6.11.1`
and fails:

```
CMake Error: failed to create symbolic link '../../lib/libQt6NetworkAuth.so.6': Permission denied
CMake Error: cmake_symlink_library: System Error: Permission denied
make[2]: *** [lib/libQt6NetworkAuth.so.6.11.1] Error 1
```

The same failure hits `libQt6Core.so` etc. in qtbase on HMDFS.

## Implementation

Two recipe-layer helpers (no source patch needed for the module):

1. `_materialize_cmake_symlink_library_rules()` — called in `build()` right after
   `cmake.configure()`. It walks the build tree `*.make` files and replaces the
   literal `$(CMAKE_COMMAND) -E cmake_symlink_library` with a call to a small
   Python helper that copies the real file to each link name
   (`shutil.copy2(source, link)`).

2. `_ensure_soname_link_copies()` — called in `package()` after
   `cmake.install()`. It replaces any installed `.so` / `.so.6` symlinks with
   file copies, so the packaged library loads without symlink support.

For qtbase (the dependency), the equivalent fix is upstream patch
`0007-cmake-build-soname-files-without-symlinks.patch` plus
`QT_NO_LIBRARY_SYMLINKS=ON`.

## Verification boundary

Shadow CI `conan create archives/q/qtnetworkauth/6.11.1 --build=missing`
succeeded on device. Upstream tests 2/2 passed (`tst_abstractoauth2`,
`tst_oauth1signature`); consumer test printed
`test_qtnetworkauth: PLAINTEXT + HMAC-SHA1 OK`. Installed
`lib/libQt6NetworkAuth.so.6.11.1` with `.so.6` and `.so` regular-file copies.

## Source

- Package: `archives/q/qtnetworkauth/6.11.1`
- Dependency verified offline: qtbase/6.11.1 (symlink fix + skip tst_qdom)
- PR: pending (issue 待补)
