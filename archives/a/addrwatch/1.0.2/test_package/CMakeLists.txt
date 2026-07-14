cmake_minimum_required(VERSION 3.15)
project(test_addrwatch C)

# Find the package via Conan-generated CMakeDeps
find_package(addrwatch REQUIRED)

add_executable(test_addrwatch test.c)
target_link_libraries(test_addrwatch addrwatch::addrwatch)

enable_testing()
add_test(NAME test_addrwatch COMMAND test_addrwatch)
