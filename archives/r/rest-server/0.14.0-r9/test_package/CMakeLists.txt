cmake_minimum_required(VERSION 3.15)
project(test_rest-server C)

# Find the package via Conan-generated CMakeDeps
find_package(rest-server REQUIRED)

add_executable(test_rest-server test.c)
target_link_libraries(test_rest-server rest-server::rest-server)

enable_testing()
add_test(NAME test_rest-server COMMAND test_rest-server)
