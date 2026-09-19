cmake_minimum_required(VERSION 3.15)
project(test_ctl C)

# Find the package via Conan-generated CMakeDeps
find_package(ctl REQUIRED)

add_executable(test_ctl test.c)
target_link_libraries(test_ctl ctl::ctl)

# HarmonyOS 专项测试（OHOS 工具链真实运行，独立于上游 func 用例）
add_executable(test_ohos test_ohos.c)
target_link_libraries(test_ohos ctl::ctl)

enable_testing()
add_test(NAME test_ctl COMMAND test_ctl)
add_test(NAME test_ohos COMMAND test_ohos)
