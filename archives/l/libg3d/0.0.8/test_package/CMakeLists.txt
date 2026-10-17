cmake_minimum_required(VERSION 3.15)
project(test_libg3d C)

find_package(libg3d REQUIRED)

add_executable(test_libg3d test_libg3d.c)
target_link_libraries(test_libg3d libg3d::libg3d)

enable_testing()
add_test(NAME test_libg3d COMMAND test_libg3d)
