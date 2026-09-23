cmake_minimum_required(VERSION 3.15)
project(test_libmnl C)

find_package(libmnl REQUIRED)

add_executable(test_libmnl test.c)
target_link_libraries(test_libmnl libmnl::libmnl)

enable_testing()
add_test(NAME test_libmnl COMMAND test_libmnl)
