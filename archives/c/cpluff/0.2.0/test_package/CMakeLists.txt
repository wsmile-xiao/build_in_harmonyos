cmake_minimum_required(VERSION 3.15)
project(test_cpluff C)

find_package(cpluff REQUIRED)

add_executable(test_cpluff test_cpluff.c)
target_link_libraries(test_cpluff cpluff::cpluff)

enable_testing()
add_test(NAME test_cpluff COMMAND test_cpluff)
