cmake_minimum_required(VERSION 3.15)
project(test_msgpack-c C)

# Find the package via Conan-generated CMakeDeps
find_package(msgpack-c REQUIRED)

add_executable(test_msgpack-c test.c)
target_link_libraries(test_msgpack-c msgpack-c::msgpack-c)

enable_testing()
add_test(NAME test_msgpack-c COMMAND test_msgpack-c)
