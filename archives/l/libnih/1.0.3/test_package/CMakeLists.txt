cmake_minimum_required(VERSION 3.15)
project(test_libnih C)

find_package(libnih REQUIRED)

add_executable(test_libnih test.c)
target_link_libraries(test_libnih libnih::libnih)

enable_testing()
add_test(NAME test_libnih COMMAND test_libnih)
