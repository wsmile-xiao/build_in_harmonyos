cmake_minimum_required(VERSION 3.15)
project(test_lib1305 C)

find_package(lib1305 REQUIRED)

add_executable(test_lib1305 test.c)
target_link_libraries(test_lib1305 lib1305::lib1305)

enable_testing()
add_test(NAME test_lib1305 COMMAND test_lib1305)
