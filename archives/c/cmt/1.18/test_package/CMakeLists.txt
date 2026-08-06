cmake_minimum_required(VERSION 3.15)
project(test_cmt C)

add_executable(test_cmt test_cmt.c)
target_link_libraries(test_cmt PRIVATE ${CMAKE_DL_LIBS})
