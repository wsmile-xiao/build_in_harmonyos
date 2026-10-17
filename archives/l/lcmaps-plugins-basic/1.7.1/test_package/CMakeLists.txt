cmake_minimum_required(VERSION 3.15)
project(test_lcmaps_plugins_basic C)

add_executable(test_lcmaps_plugins_basic test.c)
target_compile_definitions(test_lcmaps_plugins_basic
    PRIVATE LCMAPS_TEST_FW_ROOT="${LCMAPS_TEST_FW_ROOT}")
# Mirror the real LCMAPS consumer topology: the test executable NEEDs
# liblcmaps_without_gsi (startup dependency, musl global symbol scope) and
# dlopen()s the plugins. musl does NOT add a dlopen(RTLD_GLOBAL) object to
# the relocation scope of subsequently dlopen'd objects, so a pure
# dlopen-based framework preload is not sufficient to relocate the plugins'
# undefined lcmaps_* references (CI run5: "Error relocating ...: lcmaps_log:
# symbol not found").
target_link_libraries(test_lcmaps_plugins_basic
    ${CMAKE_DL_LIBS}
    "${LCMAPS_TEST_FW_ROOT}/lib/liblcmaps_without_gsi.so")

enable_testing()
add_test(NAME test_lcmaps_plugins_basic COMMAND test_lcmaps_plugins_basic)
