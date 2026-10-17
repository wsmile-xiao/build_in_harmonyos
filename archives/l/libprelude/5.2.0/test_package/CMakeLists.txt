cmake_minimum_required(VERSION 3.10)
project(test_libprelude C)

# Find the package via Conan-generated CMakeDeps
find_package(libprelude REQUIRED)

add_executable(test_libprelude test.c)
target_link_libraries(test_libprelude libprelude::libprelude)

enable_testing()
add_test(NAME test_libprelude COMMAND test_libprelude)
