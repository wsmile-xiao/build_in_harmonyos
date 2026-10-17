cmake_minimum_required(VERSION 3.15)
project(test_protobuf_c C)

find_package(protobuf-c REQUIRED)

add_executable(test_protobuf_c test.c)
target_link_libraries(test_protobuf_c protobuf-c::protobuf-c)

enable_testing()
add_test(NAME test_protobuf_c COMMAND test_protobuf_c)
