cmake_minimum_required(VERSION 3.15)
project(qsopt_ex_test LANGUAGES C)

find_package(qsopt_ex CONFIG REQUIRED)
add_executable(qsopt_ex_test test.c)
target_link_libraries(qsopt_ex_test PRIVATE qsopt_ex::qsopt_ex)
