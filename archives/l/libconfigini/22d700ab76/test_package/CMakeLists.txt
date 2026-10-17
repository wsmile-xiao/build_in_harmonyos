cmake_minimum_required(VERSION 3.15)
project(test_libconfigini C)

# Find the package via Conan-generated CMakeDeps
find_package(libconfigini REQUIRED)

# Consumer test (R34): exercises the installed public API
add_executable(test_libconfigini test.c)
target_link_libraries(test_libconfigini libconfigini::libconfigini)

# HarmonyOS specialty test (upstream-free, OHOS platform semantics)
add_executable(test_ohos test_ohos.c)
target_link_libraries(test_ohos libconfigini::libconfigini)

enable_testing()
add_test(NAME test_libconfigini COMMAND test_libconfigini)
add_test(NAME test_ohos COMMAND test_ohos)
