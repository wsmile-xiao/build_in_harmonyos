cmake_minimum_required(VERSION 3.15)
project(test_uptimed C)

# Find the package via Conan-generated CMakeDeps
find_package(uptimed REQUIRED)

add_executable(test_uptimed test.c)
target_link_libraries(test_uptimed uptimed::uptimed)

enable_testing()
add_test(NAME test_uptimed COMMAND test_uptimed)
