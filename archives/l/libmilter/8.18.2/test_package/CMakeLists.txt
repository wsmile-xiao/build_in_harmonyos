cmake_minimum_required(VERSION 3.15)
project(test_milter LANGUAGES C)

find_package(libmilter CONFIG REQUIRED)

add_executable(test_milter test_milter.c)
target_link_libraries(test_milter PRIVATE libmilter::libmilter)

enable_testing()
add_test(NAME test_milter COMMAND test_milter)
