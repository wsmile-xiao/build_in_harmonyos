cmake_minimum_required(VERSION 3.15)
project(test_qttranslations C)

add_executable(test_qttranslations test.c)

enable_testing()
add_test(NAME test_qttranslations COMMAND test_qttranslations)
