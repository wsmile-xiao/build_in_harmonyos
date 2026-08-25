cmake_minimum_required(VERSION 3.15)
project(test_zbar C)

find_package(zbar REQUIRED)

add_executable(test_zbar test_zbar.c)
target_link_libraries(test_zbar PRIVATE zbar::zbar)

enable_testing()
add_test(NAME test_zbar
         COMMAND test_zbar
         WORKING_DIRECTORY ${CMAKE_CURRENT_BINARY_DIR})
