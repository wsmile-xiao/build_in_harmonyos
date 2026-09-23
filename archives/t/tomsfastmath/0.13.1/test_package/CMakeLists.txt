cmake_minimum_required(VERSION 3.15)
project(test_tomsfastmath C)

# Find the package via Conan-generated CMakeDeps
find_package(tomsfastmath REQUIRED)

add_executable(test_tomsfastmath test_tomsfastmath.c)
target_link_libraries(test_tomsfastmath tomsfastmath::tomsfastmath)
set_target_properties(test_tomsfastmath PROPERTIES C_STANDARD 99)

enable_testing()
add_test(NAME test_tomsfastmath COMMAND test_tomsfastmath)
