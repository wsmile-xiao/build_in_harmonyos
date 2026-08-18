cmake_minimum_required(VERSION 3.15)
project(test_xclip C)

# xclip 是命令行工具（无可链接库），测试直接运行被测包二进制
add_executable(test_xclip test.c)

enable_testing()
add_test(NAME test_xclip COMMAND test_xclip)
