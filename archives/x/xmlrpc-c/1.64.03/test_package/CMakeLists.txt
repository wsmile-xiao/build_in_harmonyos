cmake_minimum_required(VERSION 3.15)
project(test_xmlrpc_c C)

find_package(xmlrpc-c REQUIRED)

add_executable(test_xmlrpc_c test.c)
target_link_libraries(test_xmlrpc_c PRIVATE xmlrpc-c::xmlrpc-c)

enable_testing()
add_test(NAME test_xmlrpc_c COMMAND test_xmlrpc_c)
