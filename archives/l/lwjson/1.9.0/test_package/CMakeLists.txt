cmake_minimum_required(VERSION 3.15)
project(test_lwjson C)

# Find the package via Conan-generated CMakeDeps
find_package(lwjson REQUIRED)

# Consumer test: parse + find + value access via public API
add_executable(test_lwjson test.c)
target_link_libraries(test_lwjson lwjson::lwjson)

# HarmonyOS/aarch64 specialty test (UTF-8 + token-budget + deep nesting)
add_executable(test_ohos test_ohos.c)
target_link_libraries(test_ohos lwjson::lwjson)

enable_testing()
add_test(NAME test_lwjson COMMAND test_lwjson)
add_test(NAME test_ohos COMMAND test_ohos)