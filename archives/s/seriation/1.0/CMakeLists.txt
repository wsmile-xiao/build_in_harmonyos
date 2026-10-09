cmake_minimum_required(VERSION 3.16)
project(seriation C)

# 上游没有提供任何构建脚本（Debian 原包只有 cfm-seriation.c + LICENSE +
# README.md + 演示数据），故这里只声明「单源文件编成可执行文件」。
# 编译器与 sysroot 全部来自 Conan 生成的 conan_toolchain.cmake。
#
# 可执行文件沿用上游自己写死的名字 cfm_seriation：print_help() 打印的是
# "Usage: ./cfm_seriation"，改名会让帮助文本与实际程序名对不上。
add_executable(cfm_seriation cfm-seriation.c)
target_compile_options(cfm_seriation PRIVATE -w)
target_compile_options(cfm_seriation PRIVATE -O2)
set_property(TARGET cfm_seriation PROPERTY C_STANDARD 99)

set_target_properties(cfm_seriation PROPERTIES
    OUTPUT_NAME "cfm_seriation"
    RUNTIME_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}")
