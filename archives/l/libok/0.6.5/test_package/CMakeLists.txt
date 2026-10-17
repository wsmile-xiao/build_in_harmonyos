cmake_minimum_required(VERSION 3.15)
project(test_libok C)

# Find the package via Conan-generated CMakeDeps
find_package(libok REQUIRED)

add_executable(test_libok test.c)
target_link_libraries(test_libok libok::libok)

# 鸿蒙特有测试（r02）：仅用公开头文件/API 验证 OHOS 目标上
# libok TAP 输出管线（计划行/计数/失败检测/汇总），见 test_ohos.c
add_executable(test_ohos test_ohos.c)
target_link_libraries(test_ohos libok::libok)

enable_testing()
add_test(NAME test_libok COMMAND test_libok)
add_test(NAME test_ohos COMMAND test_ohos)
