cmake_minimum_required(VERSION 3.15)
project(test_shoco C)

# Find the package via Conan-generated CMakeDeps
find_package(shoco REQUIRED)

add_executable(test_shoco test.c)
target_link_libraries(test_shoco shoco::shoco)

enable_testing()
add_test(NAME test_shoco COMMAND test_shoco)
