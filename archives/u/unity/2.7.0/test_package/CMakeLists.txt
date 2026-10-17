cmake_minimum_required(VERSION 3.15)
project(unity_test_package LANGUAGES C)

find_package(unity REQUIRED)

# 冒烟测试：真实链接 libunity.so（被测库核心），跑一个 UnityBegin/RUN_TEST/UNITY_END 完整生命周期
# 注：UNITY_OUTPUT_CHAR 为函数式宏，CMake 无法可靠传命令行（编译器告警），
#     改为在测试源码内 #define（include unity.h 之前）。
add_executable(test_unity test_unity.c)
target_link_libraries(test_unity PRIVATE unity::unity)

enable_testing()
add_test(NAME test_unity COMMAND test_unity)

# 鸿蒙特有测试：版本头身份 + 核心断言 + double 断言 + 输出字符钩子（4 用例）
# UNITY_INCLUDE_DOUBLE 须库侧与消费者侧同时开启（与上游 test/Makefile doubles
# 套件同款；库侧符号已在 conanfile build() 编译时开启）
add_executable(test_unity_ohos test_unity_ohos.c)
target_link_libraries(test_unity_ohos PRIVATE unity::unity)
target_compile_definitions(test_unity_ohos PRIVATE UNITY_INCLUDE_DOUBLE)
add_test(NAME test_unity_ohos COMMAND test_unity_ohos)
