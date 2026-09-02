# Draft: eigen CMake HarmonyOS warning triage

> Source event: `eigen/3.4.1` OHOS shadow CI on 2026-08-28.
> Draft only. Do not promote to `knowledge/graph/` without reviewer assignment.

## Problem

The OHOS Conan toolchain maps the target to a HarmonyOS CMake system name. CMake
4.1.2 may print the familiar platform warning:

```text
System is unknown to cmake, create:
Platform/HarmonyOS
```

For compiled shared libraries this can affect `UNIX`, SONAME flags, or upstream
platform routing. For `eigen/3.4.1`, the package itself is header-only and the
consumer test only needs the compiler, C++ standard mode, include paths, and
Conan-generated package metadata.

## Recommended triage

Treat the warning by checking the project surface, not by patching reflexively:

1. If the package builds shared libraries, exports versioned `.so` files, or
   depends on `UNIX`/`OS_LINUX` style branches, use the existing CMake
   HarmonyOS platform knowledge and verify SONAME/platform macros.
2. If the package is header-only, has no library link step, and CMake configure
   and consumer build both complete, record the warning as non-blocking.
3. Do not force `CMAKE_SYSTEM_NAME=Linux` only to silence the message; that can
   hide target identity differences from downstream consumers.
4. For consumer validation, prefer `find_package(Eigen3 REQUIRED)` and the
   generated `Eigen3::Eigen` target so the package metadata is still exercised.

## Evidence from eigen

The final shadow CI run passed despite the platform warning:

- `L0_RESULT=pass: all checks passed`
- `L1_RESULT=pass: test_package executed`
- `test_package` compiled and ran `test_eigen`
- runtime output: `eigen smoke test: PASS (matmul + norm OK)`

There was no shared object to inspect, so no SONAME claim is made for eigen.
The validated contract is the installed header tree and consumer CMake target.

## Relation to existing knowledge

Existing entries cover the general `CMAKE_SYSTEM_NAME=HarmonyOS` issue and the
cases where missing `Platform/HarmonyOS.cmake` breaks shared-library SONAME or
Unix-like platform branches. This draft adds the eigen-specific triage boundary:
for a header-only CMake package, the warning can be non-fatal when the consumer
configure, build, run, and negative test all succeed.

## Boundaries

This is not a blanket rule for CMake projects. The same warning must be
escalated for packages that compile libraries, install executables, depend on
platform-specific source files, or ship versioned shared objects.
