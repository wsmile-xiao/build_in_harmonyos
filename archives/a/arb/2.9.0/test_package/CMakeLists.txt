cmake_minimum_required(VERSION 3.15)
project(test_arb C)

# Find the package via Conan-generated CMakeDeps
find_package(arb REQUIRED)

add_executable(test_arb test.c)
target_link_libraries(test_arb arb::arb)

enable_testing()
add_test(NAME test_arb COMMAND test_arb)
