cmake_minimum_required(VERSION 3.15)
project(test_libunistring C)

find_package(libunistring REQUIRED)

add_executable(test_libunistring test.c)
target_link_libraries(test_libunistring libunistring::libunistring)

enable_testing()
add_test(NAME test_libunistring COMMAND test_libunistring)
