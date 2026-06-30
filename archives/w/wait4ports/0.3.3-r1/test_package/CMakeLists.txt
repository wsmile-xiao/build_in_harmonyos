cmake_minimum_required(VERSION 3.15)
project(test_wait4ports C)

# Find the package via Conan-generated CMakeDeps
find_package(wait4ports REQUIRED)

add_executable(test_wait4ports test.c)
target_link_libraries(test_wait4ports wait4ports::wait4ports)

enable_testing()
add_test(NAME test_wait4ports COMMAND test_wait4ports)
