cmake_minimum_required(VERSION 3.16)
project(test_chsrc C)

enable_testing()

# R34: C 测试程序在运行时通过 system("chsrc --version") 验证二进制可执行
add_executable(test_chsrc src/test_chsrc.c)
add_test(NAME chsrc_version COMMAND test_chsrc)
