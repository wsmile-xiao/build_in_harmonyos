cmake_minimum_required(VERSION 3.15)
project(test_riemann-c-client C)

# Find the package via Conan-generated CMakeDeps
find_package(riemann-c-client REQUIRED)

add_executable(test_riemann-c-client test.c)
target_link_libraries(test_riemann-c-client riemann-c-client::riemann-client)

enable_testing()
add_test(NAME test_riemann-c-client COMMAND test_riemann-c-client)
