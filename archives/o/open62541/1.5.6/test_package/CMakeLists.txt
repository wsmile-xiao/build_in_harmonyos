cmake_minimum_required(VERSION 3.15)
project(test_open62541 C)

find_package(open62541 REQUIRED CONFIG)

add_executable(test_open62541 test.c)
target_link_libraries(test_open62541 PRIVATE open62541::open62541)

enable_testing()
add_test(NAME open62541_consumer COMMAND test_open62541)
