cmake_minimum_required(VERSION 3.15)
project(test_routino C)

find_package(routino REQUIRED)

add_executable(test_routino test_routino.c)
target_link_libraries(test_routino routino::routino)

enable_testing()
add_test(NAME test_routino COMMAND test_routino)
