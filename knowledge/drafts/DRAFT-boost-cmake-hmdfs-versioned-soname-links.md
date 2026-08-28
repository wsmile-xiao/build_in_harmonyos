# DRAFT: Boost CMake versioned shared-library links on HarmonyOS PC

> Status: Draft | Updated: 2026-08-26
> Source event: `boost/1.90.0.2.1` CMake package adaptation
> Task hall: `4415`
> PR: https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos/merge_requests/6712

## Summary

Boost's CMake release has its own install helper for shared libraries. On OHOS,
the package staging filesystem and Conan consumer metadata work best when Boost
installs the unversioned shared libraries that downstream CMakeDeps targets will
actually consume, while the ELF files still carry usable `DT_SONAME` metadata.

For Boost.Python this matters because the package must provide
`libboost_python312.so` cleanly, without relying on versioned install aliases that
may not be representable or useful in the OHOS package layout.

## Symptoms

This pattern is relevant when logs or package layout show:

- `BoostInstall.cmake` participating in shared-library installation.
- Versioned `libboost_*.so.*` outputs or symlink-style install entries.
- HMDFS or package staging errors around link creation.
- Consumer metadata that points at a library name different from the installed
  unversioned Boost library.

## Root Cause

Boost's CMake install helper can generate versioned shared-library install
entries. That is normal for many Linux layouts, but on OHOS/HMDFS it can produce
fragile packaging behavior. Conan consumers generally need stable component
targets and the real packaged library files, not a collection of install-time
aliases.

## Adaptation Pattern

On OHOS, enable the Boost variable that suppresses versioned library installation
and ensure `BoostInstall.cmake` actually respects it:

```python
tc.variables["BOOST_INSTALL_NO_VERSIONED_LIBS"] = True
```

Patch the Boost CMake helper so the versioned install block is gated, but keep
an explicit unversioned SONAME on shared targets:

```diff
+  if(TYPE STREQUAL "SHARED_LIBRARY" AND BOOST_INSTALL_NO_VERSIONED_LIBS)
+    target_link_options(${LIB} PRIVATE "-Wl,-soname,$<TARGET_FILE_NAME:${LIB}>")
+  endif()
+
-  if(TYPE STREQUAL "SHARED_LIBRARY" OR TYPE STREQUAL "EXECUTABLE")
+  if((TYPE STREQUAL "SHARED_LIBRARY" OR TYPE STREQUAL "EXECUTABLE") AND NOT BOOST_INSTALL_NO_VERSIONED_LIBS)
```

Keep the fix scoped to Boost's install behavior. Do not rewrite downstream
consumer targets to compensate for a broken package layout.

## Validation

After packaging, verify:

1. The package contains unversioned `libboost_*.so` files for requested compiled
   components.
2. `package_info()` maps the actual packaged names into the expected Conan
   components.
3. A consumer can resolve `Boost::filesystem`, `Boost::program_options`,
   `Boost::system`, and `Boost::python312`.
4. The consumer executable runs on OHOS after normal signing and runtime setup.
5. The L5 SONAME gate sees each packaged `libboost_*.so` with a matching
   unversioned `DT_SONAME`.

The `boost/1.90.0.2.1` follow-up CI exposed that skipping Boost's `VERSION`
property also removed SONAME metadata. The scoped fix keeps unversioned install
outputs and adds `-Wl,-soname,$<TARGET_FILE_NAME:...>` per shared target.

## Do Not

- Do not create a post-package symlink farm to mask CMake install behavior.
- Do not copy versioned and unversioned shared libraries blindly; that can
  desynchronize filenames, SONAMEs, and generated CMake targets.
- Do not switch the package to static-only to avoid validating the shared
  library path when downstream consumers need shared Boost.Python.
