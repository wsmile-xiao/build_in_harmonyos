cmake_minimum_required(VERSION 3.15)
project(test_libblobmsg C)

find_package(libblobmsg REQUIRED)

add_executable(test_libblobmsg test.c)
target_link_libraries(test_libblobmsg libblobmsg::libblobmsg)

enable_testing()
add_test(NAME test_libblobmsg COMMAND test_libblobmsg)
