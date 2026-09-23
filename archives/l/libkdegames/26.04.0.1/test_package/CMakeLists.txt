cmake_minimum_required(VERSION 3.16)
project(test_libkdegames CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(Qt6 REQUIRED COMPONENTS Core Gui Widgets)
# Individual KF6 component configs (KF6 umbrella Config is not shipped).
find_package(KF6Config REQUIRED)
find_package(KF6I18n REQUIRED)
find_package(KDEGames6 REQUIRED)

add_executable(test_libkdegames test.cpp)
target_link_libraries(test_libkdegames
    KDEGames6
    KF6::ConfigCore
    KF6::I18n
    Qt6::Core
    Qt6::Gui
    Qt6::Widgets
)

# OHOS-specific assertions: openal audio backend wiring (E285), openal-soft
# Null-backend playback without a real audio device, and local highscore
# roundtrip through the user-writable HOME (musl/QStandardPaths behavior).
add_executable(test_ohos test_ohos.cpp)
target_link_libraries(test_ohos
    KDEGames6
    Qt6::Core
)

enable_testing()

# ctest replaces the test process environment when the ENVIRONMENT property
# is set, which drops the conan-provided loader path. The run_test.sh wrapper
# re-exports LD_LIBRARY_PATH (from the LKG_TEST_LIB_DIRS cache variable that
# conanfile.py generate() fills with every dependency lib dir) and the
# offscreen Qt platform, then execs the test binary so the exit code
# propagates to ctest.
set(_lkg_test_runner "${CMAKE_CURRENT_LIST_DIR}/run_test.sh")

add_test(
    NAME test_libkdegames
    COMMAND ${_lkg_test_runner} $<TARGET_FILE:test_libkdegames>
)
add_test(
    NAME test_ohos
    COMMAND ${_lkg_test_runner} $<TARGET_FILE:test_ohos>
)

# Pass the loader path through to the wrapper (ctest keeps this property in
# the child environment together with the wrapper's own exports).
set_tests_properties(test_libkdegames PROPERTIES
    ENVIRONMENT "LKG_TEST_LIB_DIRS=${LKG_TEST_LIB_DIRS}"
)
set_tests_properties(test_ohos PROPERTIES
    ENVIRONMENT "LKG_TEST_LIB_DIRS=${LKG_TEST_LIB_DIRS}"
)
