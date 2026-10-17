cmake_minimum_required(VERSION 3.15)
project(test_zmq C)

find_package(ZeroMQ REQUIRED)

add_executable(test_zmq test_zmq.c)
target_link_libraries(test_zmq PRIVATE libzmq)

enable_testing()
add_test(NAME test_zmq COMMAND test_zmq)
