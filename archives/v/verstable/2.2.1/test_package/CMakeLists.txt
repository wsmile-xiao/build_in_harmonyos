cmake_minimum_required(VERSION 3.15)
project(test_verstable C)

# Find the package via Conan-generated CMakeDeps
find_package(verstable REQUIRED)

add_executable(test_verstable test.c)
target_link_libraries(test_verstable verstable::verstable)

enable_testing()
add_test(NAME test_verstable COMMAND test_verstable)
