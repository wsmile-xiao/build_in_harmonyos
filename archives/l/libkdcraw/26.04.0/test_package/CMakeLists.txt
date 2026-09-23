cmake_minimum_required(VERSION 3.16)
project(test_libkdcraw CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# KDcrawQt6 is the upstream CMake package name (KDcrawQt6Config.cmake);
# the imported target is KDcrawQt6 (EXPORT_NAME, empty namespace).
find_package(Qt6 REQUIRED COMPONENTS Core Gui)
find_package(KDcrawQt6 REQUIRED)

add_executable(test_libkdcraw test.cpp)
target_link_libraries(test_libkdcraw
    KDcrawQt6
    Qt6::Core
    Qt6::Gui
)

enable_testing()

# ctest replaces the test process environment when the ENVIRONMENT property
# is set, which drops the conan-provided loader path. The run_test.sh wrapper
# re-exports LD_LIBRARY_PATH (from the LKD_TEST_LIB_DIRS cache variable that
# conanfile.py generate() fills with every dependency lib dir) and the
# offscreen Qt platform, then execs the test binary so the exit code
# propagates.
set(_lkd_test_runner "${CMAKE_CURRENT_LIST_DIR}/run_test.sh")

add_test(
    NAME test_libkdcraw
    COMMAND ${_lkd_test_runner} $<TARGET_FILE:test_libkdcraw>
)

# Pass the loader path through to the wrapper (ctest keeps this property in
# the child environment together with the wrapper's own exports).
set_tests_properties(test_libkdcraw PROPERTIES
    ENVIRONMENT "LKD_TEST_LIB_DIRS=${LKD_TEST_LIB_DIRS}"
)
