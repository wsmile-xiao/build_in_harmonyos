cmake_minimum_required(VERSION 3.16)
project(test_convlit C)

enable_testing()

# 与 multitail 相同思路：test_package 的 C 测试程序在运行时以 popen 捕获
# clit 无参数输出（版本标题 + 使用说明），输出非空即 PASS。
# clit 无参数会打印标题后返回 -1（shell 层 exit 255），因此不依赖退出码。
add_executable(test_convlit src/test_convlit.c)
set(CLIT_PATH "clit" CACHE STRING "Path to clit executable")
add_test(NAME convlit_run COMMAND test_convlit "${CLIT_PATH}")
