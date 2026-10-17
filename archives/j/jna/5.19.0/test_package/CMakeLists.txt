cmake_minimum_required(VERSION 3.15)
project(test_jna C)

find_package(jna REQUIRED)

add_executable(test_jna test_jna.c)
target_link_libraries(test_jna jna::jna ${CMAKE_DL_LIBS})

enable_testing()
add_test(NAME test_jna COMMAND test_jna)
