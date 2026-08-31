cmake_minimum_required(VERSION 3.15)
project(test_lhasa C)

find_package(lhasa REQUIRED)

add_executable(test_lhasa test.c)
target_link_libraries(test_lhasa lhasa::lhasa)

enable_testing()
add_test(NAME test_lhasa COMMAND test_lhasa)