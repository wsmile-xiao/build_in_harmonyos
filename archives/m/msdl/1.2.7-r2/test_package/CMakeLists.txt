cmake_minimum_required(VERSION 3.15)
project(test_msdl C)

# msdl 是纯 C 应用（无库、无头文件），测试程序也用纯 C 编译；
# 不链接任何 msdl 目标 —— 测试通过 fork+exec 运行包内 msdl 二进制。
add_executable(test_msdl test_msdl.c)
