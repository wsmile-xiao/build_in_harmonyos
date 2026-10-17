cmake_minimum_required(VERSION 3.15)
project(test_fcgi2 C)

# Find the package via Conan-generated CMakeDeps
find_package(fcgi2 REQUIRED)

add_executable(test_fcgi2 test.c)
target_link_libraries(test_fcgi2 fcgi2::fcgi2)

enable_testing()
add_test(NAME test_fcgi2 COMMAND test_fcgi2)
