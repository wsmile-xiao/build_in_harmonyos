cmake_minimum_required(VERSION 3.15)
project(test_lockfree-queue C)

# Find the package via Conan-generated CMakeDeps
find_package(lockfree-queue REQUIRED)

add_executable(test_lockfree-queue test.c)
target_link_libraries(test_lockfree-queue lockfree-queue::lockfree-queue)
target_link_libraries(test_lockfree-queue pthread)

# HarmonyOS-specific test (R02 required evidence key: harmonyos_specific_test)
add_executable(harmonyos_specific_test test_harmonyos.c)
target_link_libraries(harmonyos_specific_test lockfree-queue::lockfree-queue)
target_link_libraries(harmonyos_specific_test pthread)

enable_testing()
add_test(NAME test_lockfree-queue COMMAND test_lockfree-queue)
add_test(NAME harmonyos_specific_test COMMAND harmonyos_specific_test)
