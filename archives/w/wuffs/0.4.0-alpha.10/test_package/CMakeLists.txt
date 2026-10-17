cmake_minimum_required(VERSION 3.15)
project(test_wuffs C CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Resolved through the Conan-generated CMakeDeps files (wuffs-config.cmake).
find_package(wuffs REQUIRED)

# ── Consumer program: three translation units ────────────────────────────────
# The implementation translation unit, a second C translation unit that only
# sees the header, and a C++ translation unit that uses Wuffs' C++ layer.
add_executable(test_wuffs
    test_wuffs.c
    test_wuffs_header_only_tu.c
    test_wuffs_cpp.cpp
)
target_link_libraries(test_wuffs PRIVATE wuffs::wuffs)

# ── HarmonyOS platform program: one source, two architecture builds ──────────
# wuffs selects CPU-architecture-specific code paths at compile time. On OHOS PC
# (aarch64) the shipped build takes the NEON path, and that path is gated on
# platform capabilities (little-endian, working unaligned loads/stores). These
# two executables come from the SAME source:
#
#   ohos_platform_test           default      -> aarch64 fast paths enabled
#   ohos_platform_test_portable  AVOID_CPU_ARCH -> portable C only
#
# The source asserts, in both directions, which path the library reports as
# selected, so the two builds provably exercise different implementations while
# both having to satisfy the same known-answer assertions (including decoding
# from 16 unaligned input offsets). Agreement between them is therefore a real
# NEON-vs-portable equivalence result.
add_executable(ohos_platform_test ohos_platform_test.c)
target_link_libraries(ohos_platform_test PRIVATE wuffs::wuffs)

add_executable(ohos_platform_test_portable ohos_platform_test.c)
target_link_libraries(ohos_platform_test_portable PRIVATE wuffs::wuffs)
target_compile_definitions(ohos_platform_test_portable
    PRIVATE WUFFS_CONFIG__AVOID_CPU_ARCH)

enable_testing()
add_test(NAME test_wuffs COMMAND test_wuffs)
add_test(NAME ohos_platform_test COMMAND ohos_platform_test)
add_test(NAME ohos_platform_test_portable COMMAND ohos_platform_test_portable)
