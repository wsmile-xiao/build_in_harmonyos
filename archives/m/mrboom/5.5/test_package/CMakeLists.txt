cmake_minimum_required(VERSION 3.15)
project(test_mrboom C)

add_executable(test_mrboom test_core.c)
target_link_libraries(test_mrboom PRIVATE ${CMAKE_DL_LIBS})
