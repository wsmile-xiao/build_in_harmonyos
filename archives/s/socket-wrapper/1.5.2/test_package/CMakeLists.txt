cmake_minimum_required(VERSION 3.15)
project(test_socket_wrapper C)

add_executable(test_socket_wrapper test_socket_wrapper.c)
target_compile_definitions(
    test_socket_wrapper
    PRIVATE
        SOCKET_WRAPPER_TEST_LIBRARY="${SOCKET_WRAPPER_TEST_LIBRARY}"
)

if(CMAKE_DL_LIBS)
    target_link_libraries(test_socket_wrapper PRIVATE ${CMAKE_DL_LIBS})
endif()
