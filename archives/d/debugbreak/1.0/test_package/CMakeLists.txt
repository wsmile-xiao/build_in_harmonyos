cmake_minimum_required(VERSION 3.15)
project(test_debugbreak C)

# Find the package via Conan-generated CMakeDeps
find_package(debugbreak REQUIRED)

add_executable(test_debugbreak test.c)
target_link_libraries(test_debugbreak debugbreak::debugbreak)

# HarmonyOS PC 专属专项测试（本轮新增）：
# 编译期断言平台选择逻辑 + 运行期验证 brk #0 陷阱指令触发 SIGTRAP
add_executable(test_ohos test_ohos.c)
target_link_libraries(test_ohos debugbreak::debugbreak)

enable_testing()
add_test(NAME test_debugbreak COMMAND test_debugbreak)
add_test(NAME test_ohos COMMAND test_ohos)