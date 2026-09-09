cmake_minimum_required(VERSION 3.15)
project(test_handmade-math C)

# Find the package via Conan-generated CMakeDeps
find_package(handmade-math REQUIRED)

add_executable(test_handmade-math test.c)
target_link_libraries(test_handmade-math handmade-math::handmade-math)

enable_testing()
add_test(NAME test_handmade-math COMMAND test_handmade-math)
