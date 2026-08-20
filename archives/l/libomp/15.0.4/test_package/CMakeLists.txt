cmake_minimum_required(VERSION 3.15)
project(test_libomp C)

find_package(libomp REQUIRED)

add_executable(test_libomp test.c)
target_link_libraries(test_libomp libomp::libomp)

enable_testing()
add_test(NAME test_libomp COMMAND test_libomp)
