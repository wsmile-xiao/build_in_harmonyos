cmake_minimum_required(VERSION 3.15)
project(test_gifdec C)
set(CMAKE_C_STANDARD 99)
set(CMAKE_C_STANDARD_REQUIRED ON)

find_package(gifdec REQUIRED)

add_executable(test_gifdec test.c)
target_link_libraries(test_gifdec PRIVATE gifdec::gifdec)

enable_testing()
add_test(NAME test_gifdec
         COMMAND test_gifdec ${CMAKE_CURRENT_BINARY_DIR}/gif-tmp)
