cmake_minimum_required(VERSION 3.15)
project(test_package CXX)

find_package(muparserx CONFIG REQUIRED)

add_executable(test_package test_package.cpp)
target_link_libraries(test_package PRIVATE muparserx::muparserx)

# HarmonyOS 专项测试：真实调用 muparserx API 验证 OHOS 兼容性行为
add_executable(harmony_special_test harmony_special_test.cpp)
target_link_libraries(harmony_special_test PRIVATE muparserx::muparserx)