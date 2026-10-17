cmake_minimum_required(VERSION 3.15)
project(test_imageworsener C)

find_package(imageworsener CONFIG REQUIRED)

add_executable(test_imageworsener test_imageworsener.c)
target_link_libraries(test_imageworsener PRIVATE imageworsener::imageworsener)

enable_testing()
add_test(NAME test_imageworsener COMMAND test_imageworsener)
