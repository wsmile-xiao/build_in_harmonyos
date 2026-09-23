# Draft: CMake GNUInstallDirs platform branch missing HarmonyOS

> Source event: `libguarded/2.0.1` (CopperSpice cs_libguarded) OHOS device adaptation on 2026-09-04.
> Draft only. Do not promote to `knowledge/graph/` without reviewer assignment.

## Problem

Some upstream CMake projects gate `include(GNUInstallDirs)` behind a platform
branch instead of calling it unconditionally:

```cmake
if (CMAKE_SYSTEM_NAME MATCHES "Darwin")
   include(GNUInstallDirs)
   set(CMAKE_INSTALL_RPATH "@executable_path")
elseif (CMAKE_SYSTEM_NAME MATCHES "(Linux|OpenBSD|FreeBSD|NetBSD|DragonFly)")
   include(GNUInstallDirs)
   set(CMAKE_INSTALL_RPATH "\$ORIGIN")
elseif (CMAKE_SYSTEM_NAME MATCHES "Windows")
   set(CMAKE_INSTALL_BINDIR bin)
   set(CMAKE_INSTALL_LIBDIR lib)
   set(CMAKE_INSTALL_INCLUDEDIR include)
endif()
```

On OpenHarmony the CMake system name is `HarmonyOS` — both when the on-device
cmake auto-detects the platform and when the OHOS-adapted Conan toolchain maps
`os=OHOS`. No branch matches, so `GNUInstallDirs` is never included and
`CMAKE_INSTALL_INCLUDEDIR` / `CMAKE_INSTALL_LIBDIR` remain **empty**.

Configure still reports a healthy-looking prefix
(`CsLibGuarded will be installed in: /usr/local`). The failure only surfaces at
install time, because every `install(... DESTINATION "${CMAKE_INSTALL_LIBDIR}/cmake/CsLibGuarded")`
degrades to an **absolute path** when the variable is empty:

```text
CMake Error at .../cmake_install.cmake:54 (file):
  file cannot create directory: /cmake/CsLibGuarded.  Maybe need
  administrative privileges.
```

## Diagnosis recipe

1. Configure succeeds but install fails very early, trying to write a
   top-level directory like `/cmake/<Pkg>` or `/<includedir>/<Pkg>`.
2. Confirm the platform chain:
   `grep -n "CMAKE_SYSTEM_NAME MATCHES" CMakeLists.txt` and check whether the
   branch that contains `include(GNUInstallDirs)` recognizes
   `OHOS`/`HarmonyOS`.
3. In the configure output, absence of GNUInstallDirs' own progress lines and
   `CMAKE_INSTALL_*` cache entries is the corroborating signal.

## Recommended fix

Extend the platform regex with **both** OpenHarmony spellings so the branch
that carries `include(GNUInstallDirs)` also runs on OHOS:

```cmake
elseif (CMAKE_SYSTEM_NAME MATCHES "(Linux|OpenBSD|FreeBSD|NetBSD|DragonFly|OHOS|HarmonyOS)")
```

Verified on libguarded/2.0.1 on an OHOS aarch64 device: after the one-line
patch, `cmake --install` produces the correct
`include/CsLibGuarded/*.h` + `lib/cmake/CsLibGuarded/` layout inside the
prefix, the interface export files install to relative destinations, and the
full upstream Catch2 suite (21/21 ctest cases) still passes. The branch also
grants the ELF `$ORIGIN` RPATH, which is correct for OHOS.

Ship it as a portability patch (Conan `patches/` + `conandata.yml`), keeping
the real platform identity (`os=OHOS` → `CMAKE_SYSTEM_NAME=HarmonyOS`).

## Fallback (packaging-only)

When an upstream patch is not acceptable, set
`CMAKE_SYSTEM_NAME=Linux` and `CMAKE_SYSTEM_PROCESSOR=aarch64` in the Conan
`CMakeToolchain` cache variables so the existing Linux branch runs
(the pattern used by `physunits-ct-cpp11/1.4.0`). This fixes the Conan package
but hides the platform identity and leaves direct on-device upstream builds
broken; treat it as a fallback, not the primary fix. Note that silencing the
platform by override is explicitly discouraged by
`DRAFT-eigen-3.4.1-cmake-harmonyos-warning-triage` when it would hide
platform-specific behavior — this case is exactly such a situation, because
the branch decides install locations.

## Relation to existing knowledge

- `E267` covers the `System is unknown to cmake` warning and source-level
  `OHOS|HarmonyOS` detection, not install-directory fallout.
- `E532` covers `if(WIN32)/elseif(UNIX)/else FATAL` configure-time fatal
  errors; here configure succeeds and the failure is a silent empty-variable
  install path.
- `E504` is the adjacent install-phase entry (RPATH_CHANGE rewriting linked
  `.so` files); the knowledge engine's closest match for this error text, yet
  a different root cause — here no RPATH rewrite happens and the failure is
  `file cannot create directory: /cmake/<Pkg>` from empty install-dir
  variables.
- `DRAFT-eigen-3.4.1-cmake-harmonyos-warning-triage` records when the warning
  is non-blocking; this entry records the opposite triage outcome: when
  platform branches carry real behavior (GNUInstallDirs, RPATH), the branch
  must be fixed instead of overridden or ignored.

The CopperSpice `cs_*` CMake skeleton shares this structure, so sibling
libraries are likely to reproduce the same failure and can reuse this fix.
