cmake_minimum_required(VERSION 3.15)
project(test_qlibc C)

# Find the package via Conan-generated CMakeDeps
find_package(qlibc REQUIRED)

add_executable(test_qlibc test.c)
target_link_libraries(test_qlibc qlibc::qlibc)

# HarmonyOS-specific consumer test (qlibc 2.5.1 R01)
add_executable(test_ohos test_ohos.c)
target_link_libraries(test_ohos qlibc::qlibc)

enable_testing()
add_test(NAME test_qlibc COMMAND test_qlibc)
add_test(NAME test_ohos COMMAND test_ohos)
