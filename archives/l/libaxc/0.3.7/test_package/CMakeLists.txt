cmake_minimum_required(VERSION 3.15)
project(test_axc C)

find_package(libaxc REQUIRED)

add_executable(test_axc test.c)
target_link_libraries(test_axc libaxc::libaxc)

enable_testing()
add_test(NAME test_axc_context COMMAND test_axc context)
add_test(NAME test_axc_buf COMMAND test_axc buf)
