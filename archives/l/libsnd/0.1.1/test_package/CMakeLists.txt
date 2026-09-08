cmake_minimum_required(VERSION 3.15)
project(test_libsnd CXX)

# Find the package via Conan-generated CMakeDeps
find_package(libsnd REQUIRED)

# L1 consumer test: exercises the packaged libsnd static library API.
add_executable(test_libsnd test.cpp)
target_link_libraries(test_libsnd libsnd::libsnd)

# HarmonyOS-specific test: verifies the library under the OHOS runtime
# (aarch64 probe, denormal handling, DSP numerical behavior).
add_executable(test_ohos ohos_specific_test.cpp)
target_link_libraries(test_ohos libsnd::libsnd)

enable_testing()
add_test(NAME test_libsnd COMMAND test_libsnd)
add_test(NAME test_ohos COMMAND test_ohos)