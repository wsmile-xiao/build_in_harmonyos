cmake_minimum_required(VERSION 3.15)
project(test_flag C)

# Find the package via Conan-generated CMakeDeps
find_package(flag REQUIRED)

add_executable(test_flag test.c)
target_link_libraries(test_flag flag::flag)

# HarmonyOS 专项测试：覆盖 flag 公开 API 完整调用面（write_usage/错误联合体/别名/边界）
add_executable(test_ohos test_ohos.c)
target_link_libraries(test_ohos flag::flag)

enable_testing()
add_test(NAME test_flag COMMAND test_flag)
add_test(NAME test_ohos COMMAND test_ohos)
