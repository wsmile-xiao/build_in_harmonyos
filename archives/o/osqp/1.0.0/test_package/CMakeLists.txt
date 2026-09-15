cmake_minimum_required(VERSION 3.15)
project(test_osqp C)

# Find the package via Conan-generated CMakeDeps
find_package(osqp REQUIRED)

add_executable(test_osqp test.c)
target_link_libraries(test_osqp osqp::osqp)

enable_testing()
add_test(NAME test_osqp COMMAND test_osqp)
