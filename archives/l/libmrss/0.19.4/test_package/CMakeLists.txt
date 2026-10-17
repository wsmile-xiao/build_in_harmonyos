cmake_minimum_required(VERSION 3.15)
project(test_libmrss C)

find_package(libmrss REQUIRED)

add_executable(test_libmrss test.c)
target_link_libraries(test_libmrss libmrss::libmrss)

enable_testing()
add_test(NAME test_libmrss COMMAND test_libmrss)
