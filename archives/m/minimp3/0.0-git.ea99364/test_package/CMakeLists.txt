cmake_minimum_required(VERSION 3.15)
project(test_minimp3 C)
set(CMAKE_C_STANDARD 99)
set(CMAKE_C_STANDARD_REQUIRED ON)

find_package(minimp3 REQUIRED)

add_executable(test_minimp3 test.c)
target_link_libraries(test_minimp3 PRIVATE minimp3::minimp3)

enable_testing()
add_test(NAME test_minimp3 COMMAND test_minimp3)
