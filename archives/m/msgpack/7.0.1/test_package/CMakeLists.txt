cmake_minimum_required(VERSION 3.15)
project(test_msgpack C)

# Find the package via Conan-generated CMakeDeps.
# The upstream config package is msgpack-c-config.cmake, target msgpack-c::msgpack-c.
find_package(msgpack-c REQUIRED)

add_executable(test_msgpack test_msgpack.c)
target_link_libraries(test_msgpack msgpack-c::msgpack-c)

enable_testing()
add_test(NAME test_msgpack COMMAND test_msgpack)
