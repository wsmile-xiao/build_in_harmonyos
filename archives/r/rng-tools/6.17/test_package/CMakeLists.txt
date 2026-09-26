cmake_minimum_required(VERSION 3.15)
project(test_rng-tools C)

# rng-tools 是纯可执行文件包（无库、无头文件导出），不做 find_package；
# 测试程序只依赖 libc（popen/strstr），通过 PATH(conanrun env) 调用
# 被测二进制 rngtest/rngd。
add_executable(test_rng-tools test.c)

enable_testing()
add_test(NAME test_rng-tools COMMAND test_rng-tools)
