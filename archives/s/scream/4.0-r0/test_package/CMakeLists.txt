cmake_minimum_required(VERSION 3.15)
project(test_scream C)

# Find the package via Conan-generated CMakeDeps
find_package(scream REQUIRED)

add_executable(test_scream test.c)
target_link_libraries(test_scream scream::scream)

enable_testing()
add_test(NAME test_scream COMMAND test_scream)
