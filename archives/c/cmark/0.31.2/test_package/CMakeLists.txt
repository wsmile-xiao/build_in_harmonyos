cmake_minimum_required(VERSION 3.14)
project(test_cmark C)

find_package(cmark REQUIRED)

add_executable(test_cmark test.c)
target_link_libraries(test_cmark cmark::cmark)

enable_testing()
add_test(NAME test_cmark COMMAND test_cmark)