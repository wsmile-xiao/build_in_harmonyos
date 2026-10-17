cmake_minimum_required(VERSION 3.10)
project(libansilove_consumer_test C)

find_package(ansilove REQUIRED)

add_executable(test_package test.c)
target_link_libraries(test_package PRIVATE ansilove::ansilove)

# 鸿蒙 PC 专项测试：AArch64/musl 编译期断言 + 真实 SGR ANSI 渲染 + 字体表索引
add_executable(test_ohos test_ohos.c)
target_link_libraries(test_ohos PRIVATE ansilove::ansilove)
