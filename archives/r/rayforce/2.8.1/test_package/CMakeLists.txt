cmake_minimum_required(VERSION 3.15)
project(test_rayforce C)

# Find the package via Conan-generated CMakeDeps
find_package(rayforce REQUIRED)

add_executable(test_rayforce test.c)
target_link_libraries(test_rayforce rayforce::rayforce)

# HarmonyOS 专项测试 (OHOS-specific special test, part of this package)
add_executable(test_rayforce_ohos test_ohos.c)
target_link_libraries(test_rayforce_ohos rayforce::rayforce)

enable_testing()
add_test(NAME test_rayforce COMMAND test_rayforce)
add_test(NAME test_rayforce_ohos COMMAND test_rayforce_ohos)