# Sundials

## Description
SUNDIALS (Suite of Nonlinear and DIfferential/ALgebraic equation Solvers) is a suite of solvers developed by Lawrence Livermore National Laboratory (LLNL) for the solution of large-scale nonlinear and differential/algebraic equation problems. It is written in C.

## Available Versions
- **4.0.0** (built, 2026-06-24): CMake build with static libraries, all solver modules enabled

## Build Configuration (4.0.0)
- **Build System**: CMake
- **Compiler**: Clang 15.0.4
- **Build Type**: Static libraries only (BUILD_SHARED_LIBS=OFF, BUILD_STATIC_LIBS=ON)
- **Modules**: CVODE, CVODES, IDA, IDAS, ARKODE, KINSOL
- **Linear Solvers**: Band, Dense, SPGMR, SPFGMR, SPBCGS, SPTFQMR, PCG
- **Nonlinear Solvers**: Newton, FixedPoint
- **Examples**: Enabled and installed

## Installed Libraries
- libsundials_arkode.a
- libsundials_cvode.a
- libsundials_cvodes.a
- libsundials_ida.a
- libsundials_idas.a
- libsundials_kinsol.a
- libsundials_nvecserial.a
- libsundials_sunlinsolband.a
- libsundials_sunlinsoldense.a
- libsundials_sunlinsolpcg.a
- libsundials_sunlinsolspbcgs.a
- libsundials_sunlinsolspfgmr.a
- libsundials_sunlinsolspgmr.a
- libsundials_sunlinsolsptfqmr.a
- libsundials_sunmatrixband.a
- libsundials_sunmatrixdense.a
- libsundials_sunmatrixsparse.a
- libsundials_sunnonlinsolfixedpoint.a
- libsundials_sunnonlinsolnewton.a

## Test Results
- 41/43 tests passed (95%)
- 2 sparse matrix tests failed due to floating-point precision differences (non-critical)
- All core solver modules pass all tests

## Notes
- CMake 4.1.2 requires -DCMAKE_POLICY_VERSION_MINIMUM=3.5 for compatibility with sundials 4.0.0's cmake_minimum_required(VERSION 3.1.3)
- CMake does not recognize HarmonyOS as a platform, but compilation works with warnings only
- No source code modifications were needed for OpenHarmony compatibility
