cmake_minimum_required(VERSION 3.15)
project(test_dsocks C)

find_package(dsocks REQUIRED)

add_executable(test_dsocks test.c)
target_link_libraries(test_dsocks dsocks::dsocks ${CMAKE_DL_LIBS})

enable_testing()
add_test(NAME test_dsocks COMMAND test_dsocks)
