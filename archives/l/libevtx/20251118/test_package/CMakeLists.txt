cmake_minimum_required(VERSION 3.15)
project(test_libevtx C)

find_package(libevtx REQUIRED)

add_executable(test_libevtx test.c)
target_link_libraries(test_libevtx libevtx::libevtx)

enable_testing()
add_test(NAME test_libevtx COMMAND test_libevtx)
