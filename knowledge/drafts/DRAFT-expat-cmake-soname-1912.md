# DRAFT-expat-cmake-soname-1912 - Disable CMake versioned shared-library symlinks on OHOS paths

> **Contributor**: xuguowei | **Status**: VERIFIED DRAFT | **Updated**: 2026-08-11
> **Severity**: medium | **Category**: cmake / shared-library / OHOS filesystem

## Usage

Use this pattern when a CMake package builds a shared library successfully but
fails while creating a versioned shared-object symlink on HarmonyOS PC or an
OHOS/HMDFS-backed build path.

## Scope

- CMake packages that produce a shared library with versioned names such as
  `libfoo.so.1`.
- Build paths where creating symlinks is not supported or returns
  `Permission denied`.
- Recipes where consumers still need a valid ELF `SONAME` and must not record a
  Conan cache absolute path in `DT_NEEDED`.

This is not a fix for missing link permissions or a broken compiler. Apply it
only after confirming the failing operation is CMake's versioned shared-library
symlink creation.

## Symptom

The failure appears before `package()` and before any post-install cleanup can
run:

```text
CMake Error: failed to create symbolic link 'libexpat.so.1': Permission denied
CMake Error: cmake_symlink_library: System Error: Permission denied
```

If SONAME generation is disabled entirely, a downstream shared library can
record the producer's absolute Conan cache path in `DT_NEEDED`, making the
consumer non-relocatable.

## Root Cause

CMake's default Unix shared-library rules can create a versioned real library
and one or more symlinks. Some HarmonyOS PC build paths reject symlink creation,
so the build fails even though the compiled library is otherwise valid.

Disabling SONAME entirely is also unsafe. Without a SONAME, the linker can copy
the exact input path into downstream `DT_NEEDED`, tying consumers to a specific
Conan package cache hash.

## Implementation

Keep SONAME emission enabled, but ask CMake not to use versioned shared-object
names or symlinks:

```python
tc.variables["CMAKE_PLATFORM_NO_VERSIONED_SONAME"] = True
tc.variables["CMAKE_SHARED_LIBRARY_SONAME_C_FLAG"] = "-Wl,-soname,"
```

For expat this produces an unversioned real `libexpat.so` with an ELF SONAME of
`libexpat.so`. CMake no longer tries to create `libexpat.so.1`, and downstream
libraries record the relocatable SONAME instead of the package-cache path.

## Forbidden Approaches

- Do not remove SONAME emission completely.
- Do not rely on deleting symlinks in `package()` when the build already fails
  before install.
- Do not add broad filesystem permission workarounds such as changing the whole
  build tree mode.
- Do not claim success from compilation alone; inspect or test the produced
  shared library.

## Verification

1. Run a clean Conan build on the HarmonyOS PC CI or target runner.
2. Require CMake build and install to complete without creating the failing
   versioned symlink.
3. Inspect the produced shared library and require:

   ```text
   Library soname: [libexpat.so]
   ```

4. Build and run a `test_package` consumer that dynamically loads the library
   and calls real exported APIs.
5. Run a negative dependency test by moving package `lib/` and `include/` away
   and confirming the consumer genuinely depends on the packaged artifact.

## Validated Example

`expat/2.8.2.1.1` uses this pattern after `vips/8.18.4` shadow CI exposed the
`libexpat.so.1` symlink failure. The follow-up recipe keeps a relocatable SONAME
while producing only `libexpat.so`.

Shadow CI passed for `archives/e/expat/2.8.2.1.1`. The package built and
installed successfully, `binary-sign-tool` signed `libexpat.so`, and
`llvm-readelf -d libexpat.so` reported `Library soname: [libexpat.so]`. The
Conan `test_package` compiled and ran a C smoke test that `dlopen`s the library,
resolves `XML_ParserCreate`, `XML_Parse`, and `XML_ParserFree`, parses a small
XML document, and prints `expat: dlopen libexpat.so ok`.
