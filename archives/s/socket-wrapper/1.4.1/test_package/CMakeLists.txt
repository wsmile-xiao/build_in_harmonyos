cmake_minimum_required(VERSION 3.15)
project(test_socket_wrapper C)

find_package(socket_wrapper CONFIG REQUIRED)

add_executable(test_socket_wrapper test_socket_wrapper.c)
target_link_libraries(
    test_socket_wrapper
    PRIVATE
        socket_wrapper::socket_wrapper
)
