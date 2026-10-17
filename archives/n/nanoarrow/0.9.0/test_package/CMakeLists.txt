cmake_minimum_required(VERSION 3.15)
project(test_nanoarrow C)

find_package(nanoarrow REQUIRED)

add_executable(test_nanoarrow test.c)
target_link_libraries(test_nanoarrow nanoarrow::nanoarrow)

enable_testing()
add_test(NAME test_nanoarrow COMMAND test_nanoarrow)
