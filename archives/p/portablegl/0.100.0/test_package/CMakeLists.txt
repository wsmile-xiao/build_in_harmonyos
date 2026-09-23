cmake_minimum_required(VERSION 3.15)
project(test_portablegl C)

# Find the package via Conan-generated CMakeDeps
find_package(portablegl REQUIRED)

add_executable(test_portablegl test.c)
target_link_libraries(test_portablegl portablegl::portablegl)

enable_testing()
add_test(NAME test_portablegl COMMAND test_portablegl)
