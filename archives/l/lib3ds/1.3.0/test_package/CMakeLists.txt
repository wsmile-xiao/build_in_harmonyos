cmake_minimum_required(VERSION 3.15)
project(test_lib3ds C)

find_package(lib3ds REQUIRED)

add_executable(test_lib3ds test.c)
target_link_libraries(test_lib3ds lib3ds::lib3ds)

enable_testing()
add_test(NAME test_lib3ds COMMAND test_lib3ds)
