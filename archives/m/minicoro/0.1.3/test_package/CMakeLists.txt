cmake_minimum_required(VERSION 3.15)
project(test_minicoro C)

find_package(minicoro CONFIG REQUIRED)

add_executable(test_minicoro test.c)
target_link_libraries(test_minicoro PRIVATE minicoro)

# HarmonyOS 专项测试：验证 aarch64 MCO_USE_ASM 实现分支、嵌套协程、
# 深度调用链 yield、自定义分配器语义
add_executable(test_ohos_platform test_ohos_platform.c)
target_link_libraries(test_ohos_platform PRIVATE minicoro)

enable_testing()
add_test(NAME test_minicoro COMMAND test_minicoro)
add_test(NAME test_ohos_platform COMMAND test_ohos_platform)