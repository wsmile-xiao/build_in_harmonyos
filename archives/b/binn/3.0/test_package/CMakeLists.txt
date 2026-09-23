cmake_minimum_required(VERSION 3.15)
project(test_binn C)

# Find the package via Conan-generated CMakeDeps
find_package(binn REQUIRED)

add_executable(test_binn test.c)
target_link_libraries(test_binn binn::binn)

# HarmonyOS/aarch64 specialty tests (wire-format endianness + UTF-8 + nesting)
add_executable(test_ohos test_ohos.c)
target_link_libraries(test_ohos binn::binn)

enable_testing()
add_test(NAME test_binn COMMAND test_binn)
add_test(NAME test_ohos COMMAND test_ohos)