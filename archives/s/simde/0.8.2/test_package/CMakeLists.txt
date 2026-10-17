cmake_minimum_required(VERSION 3.15)
project(test_simde C)

# Find the package via Conan-generated CMakeDeps
find_package(simde REQUIRED)

add_executable(test_simde test.c)
target_link_libraries(test_simde simde::simde)

enable_testing()
add_test(NAME test_simde COMMAND test_simde)
