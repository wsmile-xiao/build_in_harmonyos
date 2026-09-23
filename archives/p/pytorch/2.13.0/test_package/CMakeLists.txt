cmake_minimum_required(VERSION 3.15)
project(test_pytorch CXX)

# Find the package via Conan-generated CMakeDeps
find_package(pytorch REQUIRED)

add_executable(test_pytorch test_pytorch.cpp)
target_link_libraries(test_pytorch pytorch::pytorch)

# HarmonyOS 专项测试：运行时判定宿主平台（uname(2)），在 HarmonyOS 上校验平台身份、
# 补丁 0004 的 musl ssize_t 可见性、补丁 0001 的 group_norm 迭代器路径，以及 OHOS
# aarch64 下的复数/整数算术；非 HarmonyOS 宿主打印 SKIP 且以 0 退出（不使用平台宏）。
add_executable(test_pytorch_ohos test_pytorch_ohos.cpp)
target_link_libraries(test_pytorch_ohos pytorch::pytorch)
