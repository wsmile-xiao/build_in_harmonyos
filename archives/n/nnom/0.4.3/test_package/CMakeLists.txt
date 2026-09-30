cmake_minimum_required(VERSION 3.15)
project(test_nnom C)

# Find the package via Conan-generated CMakeDeps
find_package(nnom REQUIRED)

# 消费者用例（R34：实质调用被测库公开 API，断言模型前向运算结果）
add_executable(test_nnom test_nnom.c)
target_link_libraries(test_nnom nnom::nnom)

# HarmonyOS 专项测试（OHOS 目标上验证定点前向符号路径与 port 层可用性）
add_executable(test_ohos test_ohos.c)
target_link_libraries(test_ohos nnom::nnom)

enable_testing()
add_test(NAME test_nnom COMMAND test_nnom)
add_test(NAME test_ohos COMMAND test_ohos)