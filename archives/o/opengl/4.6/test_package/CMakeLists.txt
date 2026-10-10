cmake_minimum_required(VERSION 3.15)
project(opengl_test_package C)

include(CTest)
find_package(opengl REQUIRED)

# 消费者用例: 仅使用公开头文件/宏/类型 API
add_executable(test_package test_package.c)
target_link_libraries(test_package PRIVATE opengl::opengl)
add_test(NAME consumer COMMAND test_package)

# 鸿蒙专项: aarch64-ohos 平台语义校验
add_executable(harmonyos_test harmonyos_test.c)
target_link_libraries(harmonyos_test PRIVATE opengl::opengl)
add_test(NAME harmonyos COMMAND harmonyos_test)
