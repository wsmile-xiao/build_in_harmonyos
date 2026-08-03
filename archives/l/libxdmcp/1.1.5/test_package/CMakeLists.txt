cmake_minimum_required(VERSION 3.15)
project(test_libxdmcp C)

find_package(libxdmcp REQUIRED)

add_executable(test_libxdmcp test.c)
target_link_libraries(test_libxdmcp PRIVATE libxdmcp::libxdmcp)

enable_testing()
add_test(NAME test_libxdmcp COMMAND test_libxdmcp)