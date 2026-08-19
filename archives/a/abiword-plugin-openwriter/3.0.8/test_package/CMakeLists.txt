cmake_minimum_required(VERSION 3.15)
project(test_openwriter C)

# R34 (libgsf API surface) check: links test_openwriter.c against
# libgsf-1 + libglib-2.0 via PkgConfig IMPORTED targets.  Link-time
# pass proves the openwriter plugin's libgsf symbol surface is satisfied.
#
# We deliberately do NOT dlopen openwriter.so from this test binary.
# openwriter.so is an abiword plugin: it is dlopen'd by the abiword
# process at runtime, which provides the IE_Exp / PD_Document /
# UT_String / ... symbol pool. There is no libabiword recipe at this
# CI gate.
#
# Runtime smoke-test of the cross-compiled (OHOS/ARM64) binary is
# deferred to a separate qemu-aarch64 job outside this CI gate
# (per R-NEW 2026-08-10 / Phase 2.3).  This test_package only
# verifies link-time correctness.
find_package(PkgConfig REQUIRED)
pkg_check_modules(OPENWRITER REQUIRED openwriter-plugin)
pkg_check_modules(LIBGSF REQUIRED IMPORTED_TARGET libgsf-1)
pkg_check_modules(GLIB REQUIRED IMPORTED_TARGET glib-2.0)
message(STATUS "openwriter: openwriter-plugin ${OPENWRITER_VERSION}, "
               "libgsf ${LIBGSF_VERSION}, glib ${GLIB_VERSION}")

add_executable(test_openwriter test_openwriter.c)
target_link_libraries(test_openwriter PRIVATE
    PkgConfig::LIBGSF
    PkgConfig::GLIB)
