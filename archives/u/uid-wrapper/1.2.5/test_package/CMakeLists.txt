cmake_minimum_required(VERSION 3.15)
project(test_uid_wrapper C)

add_executable(test_uid_wrapper test_uid_wrapper.c)
target_compile_definitions(test_uid_wrapper PRIVATE _GNU_SOURCE)

if(CMAKE_DL_LIBS)
    target_link_libraries(test_uid_wrapper PRIVATE ${CMAKE_DL_LIBS})
endif()
