cmake_minimum_required(VERSION 3.16)
project(test_multitail C)

enable_testing()

# R34: C 测试程序在运行时通过 system("multitail --help") 验证二进制可执行
# find_program 在 test_package 上下文中 CMAKE_INSTALL_PREFIX 指向测试包自身前缀，
# 无法定位被测包二进制，故不在此做构建时检查。
add_executable(test_multitail src/test_multitail.c)
add_test(NAME multitail_version COMMAND test_multitail)
