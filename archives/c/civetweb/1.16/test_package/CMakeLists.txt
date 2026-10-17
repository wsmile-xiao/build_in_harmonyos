cmake_minimum_required(VERSION 3.15)
project(test_civetweb C)

# Find the package via Conan-generated CMakeDeps
find_package(civetweb REQUIRED)

add_executable(test_civetweb test.c)
target_link_libraries(test_civetweb civetweb::civetweb)

enable_testing()
add_test(NAME test_civetweb COMMAND test_civetweb)
