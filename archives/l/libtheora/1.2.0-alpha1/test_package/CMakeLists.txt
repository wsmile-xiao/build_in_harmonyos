cmake_minimum_required(VERSION 3.15)
project(test_theora C)

find_package(theora REQUIRED)

add_executable(test_theora src/test_theora.c)
target_link_libraries(test_theora theora::theoraenc theora::theoradec)

enable_testing()
add_test(NAME test_theora COMMAND test_theora)
