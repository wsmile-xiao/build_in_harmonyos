cmake_minimum_required(VERSION 3.15)
project(test_mesa C)

# Find the package via Conan-generated CMakeDeps. The target exposes the
# packaged OSMesa library and headers to this consumer.
find_package(mesa REQUIRED)

add_executable(test_mesa test.c)
target_link_libraries(test_mesa mesa::mesa)

enable_testing()
add_test(NAME test_mesa COMMAND test_mesa)
