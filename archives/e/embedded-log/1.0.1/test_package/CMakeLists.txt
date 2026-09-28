cmake_minimum_required(VERSION 3.15)
project(test_embedded-log C)

# Find the package via Conan-generated CMakeDeps
find_package(embedded-log REQUIRED)

# 消费者用例（R34：实质调用被测库公开 API，断言 hook 回调）
add_executable(test_embedded-log test.c)
target_link_libraries(test_embedded-log embedded-log::embedded-log)

# HarmonyOS 专项测试（多级别日志宏 + printk_hex 真实行为验证）
add_executable(test_ohos test_ohos.c)
target_link_libraries(test_ohos embedded-log::embedded-log)

enable_testing()
add_test(NAME test_embedded-log COMMAND test_embedded-log)
add_test(NAME test_ohos COMMAND test_ohos)
