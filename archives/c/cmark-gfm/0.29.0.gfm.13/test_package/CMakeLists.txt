cmake_minimum_required(VERSION 3.15)
project(test_cmark_gfm C)

find_package(cmark-gfm REQUIRED)

add_executable(test_cmark_gfm test.c)
target_link_libraries(test_cmark_gfm cmark-gfm::cmark-gfm)

enable_testing()
add_test(NAME test_cmark_gfm COMMAND test_cmark_gfm)
