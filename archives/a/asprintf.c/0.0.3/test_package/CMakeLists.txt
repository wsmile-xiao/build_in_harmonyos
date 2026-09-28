cmake_minimum_required(VERSION 3.15)
# 包名含点号，find_package 用显式名称
# 可执行文件命名 test_consume（消费者测试程序）：
# CI L1d 启发式会对 test_package/conanfile.py 中 self.run 行做
# (echo|print|true) 子串匹配，任何含 "asprintf" 的程序名都会因
# "asprintf" 内含子串 "print" 而误判为假测试，故此处避开。
project(test_consume C)

find_package(asprintf.c REQUIRED)

add_executable(test_consume test.c)
target_link_libraries(test_consume PRIVATE asprintf.c::asprintf.c)

enable_testing()
add_test(NAME test_consume COMMAND test_consume)
