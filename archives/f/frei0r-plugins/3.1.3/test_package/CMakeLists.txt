cmake_minimum_required(VERSION 3.15)
project(test_frei0r C)

# Find the package via Conan-generated CMakeDeps
find_package(frei0r REQUIRED)

add_executable(test_frei0r test.c)
target_link_libraries(test_frei0r PRIVATE frei0r::frei0r)

enable_testing()
add_test(NAME test_frei0r COMMAND test_frei0r)
