cmake_minimum_required(VERSION 3.15)
project(test_msgpuck C)

find_package(msgpuck REQUIRED CONFIG)

add_executable(test_msgpuck test_msgpuck.c)
target_link_libraries(test_msgpuck PRIVATE msgpuck::msgpuck)

enable_testing()
add_test(NAME msgpuck_consumer COMMAND test_msgpuck)
