cmake_minimum_required(VERSION 3.15)
project(test_cimfomfa C)

# Find the package via Conan-generated CMakeDeps
find_package(cimfomfa REQUIRED)

add_executable(test_cimfomfa test.c)
target_link_libraries(test_cimfomfa cimfomfa::cimfomfa)

# HarmonyOS-specific executable: verify the OHOS/aarch64 target and exercise
# cimfomfa against OHOS libc runtime values.
add_executable(test_cimfomfa_harmonyos test_harmonyos.c)
target_link_libraries(test_cimfomfa_harmonyos cimfomfa::cimfomfa)

enable_testing()
add_test(NAME test_cimfomfa COMMAND test_cimfomfa)
add_test(NAME test_cimfomfa_harmonyos COMMAND test_cimfomfa_harmonyos)
