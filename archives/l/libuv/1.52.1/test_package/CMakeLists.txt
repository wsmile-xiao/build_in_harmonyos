cmake_minimum_required(VERSION 3.15)
project(test_libuv C)

find_package(libuv REQUIRED)

add_executable(test_libuv test.c)
target_link_libraries(test_libuv libuv::libuv)

enable_testing()
add_test(NAME test_libuv COMMAND test_libuv)
