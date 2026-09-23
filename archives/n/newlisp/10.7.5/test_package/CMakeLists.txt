cmake_minimum_required(VERSION 3.15)
project(test_newlisp C)

enable_testing()

# 消费者冒烟：C 程序执行 newlisp 二进制并断言输出（R34 实质调用被测包二进制）
add_executable(test_newlisp test_newlisp.c)
add_test(NAME test_newlisp COMMAND test_newlisp)

# ctest 直调 newlisp 断言：(+ 1 2) 输出 3；-v 输出版本号
add_test(NAME newlisp_arith COMMAND newlisp -e "(+ 1 2)")
set_tests_properties(newlisp_arith PROPERTIES PASS_REGULAR_EXPRESSION "3")

add_test(NAME newlisp_version COMMAND newlisp -v)
set_tests_properties(newlisp_version PROPERTIES PASS_REGULAR_EXPRESSION "10\\.7\\.5")