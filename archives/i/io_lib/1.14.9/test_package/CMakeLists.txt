cmake_minimum_required(VERSION 3.15)
project(test_io_lib C)

# io_lib ships no CMake config; CMakeDeps generates one (find_package name
# = recipe name, target io_lib::io_lib).
find_package(io_lib REQUIRED CONFIG)

add_executable(test_io_lib_ztr test_io_lib_ztr.c)
target_link_libraries(test_io_lib_ztr io_lib::io_lib)

enable_testing()
add_test(NAME ztr_roundtrip COMMAND test_io_lib_ztr)
