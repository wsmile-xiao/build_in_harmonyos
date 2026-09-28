cmake_minimum_required(VERSION 3.15)
project(test_libzt C)

# Find the package via Conan-generated CMakeDeps
find_package(libzt REQUIRED)

add_executable(test_libzt test.c)
target_link_libraries(test_libzt libzt::libzt)

# HarmonyOS 专项测试：uname 鸿蒙内核标识 + aarch64 ABI 断言 + libzt API 实调
add_executable(test_ohos test_ohos.c)
target_link_libraries(test_ohos libzt::libzt)

enable_testing()
add_test(NAME test_libzt COMMAND test_libzt)
add_test(NAME test_ohos COMMAND test_ohos)
