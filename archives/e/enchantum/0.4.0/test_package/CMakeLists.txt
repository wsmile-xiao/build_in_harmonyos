cmake_minimum_required(VERSION 3.15)
project(test_enchantum CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Find the package via Conan-generated CMakeDeps
find_package(enchantum REQUIRED)

add_executable(test_enchantum test.cpp)
target_link_libraries(test_enchantum enchantum::enchantum)

enable_testing()
add_test(NAME test_enchantum COMMAND test_enchantum)

# HarmonyOS 专项测试（任务要求 5：真实可执行的 OHOS 平台用例）
# 仅当目标平台为 OHOS 时才参与编译与执行；非 OHOS 目标（如 CI 冒烟/本地
# Linux 验证）跳过，避免在非鸿蒙平台误报平台断言失败。
if(CMAKE_SYSTEM_NAME STREQUAL "HarmonyOS" OR CMAKE_SYSTEM_NAME STREQUAL "OHOS")
  add_executable(test_ohos test_ohos.cpp)
  target_link_libraries(test_ohos enchantum::enchantum)
  add_test(NAME test_ohos COMMAND test_ohos)
endif()
