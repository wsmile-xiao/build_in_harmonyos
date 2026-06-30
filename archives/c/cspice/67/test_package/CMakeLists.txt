cmake_minimum_required(VERSION 3.15)
project(test_cspice C)

# Find the package via Conan-generated CMakeDeps
find_package(cspice REQUIRED)

add_executable(test_cspice test.c)
target_link_libraries(test_cspice cspice::cspice)

enable_testing()
add_test(NAME test_cspice COMMAND test_cspice)
