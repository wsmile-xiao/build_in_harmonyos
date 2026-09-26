cmake_minimum_required(VERSION 3.15)
project(infamousplugins_test_package C)

# lv2 is a header-only Conan dependency; its header location comes from the
# .pc file that PkgConfigDeps generated for this test package.
find_package(PkgConfig REQUIRED)
pkg_check_modules(LV2 REQUIRED lv2)
include_directories(${LV2_INCLUDE_DIRS})

# consumer test: dlopen every installed bundle and really run its DSP
add_executable(test_lv2_plugins test_lv2_plugins.c)
target_link_libraries(test_lv2_plugins PRIVATE ${CMAKE_DL_LIBS} m)

# HarmonyOS specific test: AArch64/ELF identity, RTLD_NOW loading from the
# Conan package, /proc/self/maps origin, dependency chain, path hygiene
add_executable(ohos_specific_test ohos_specific_test.c)
target_link_libraries(ohos_specific_test PRIVATE ${CMAKE_DL_LIBS} m)
