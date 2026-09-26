cmake_minimum_required(VERSION 3.15)
project(test_thesias C)

# Find the package via Conan-generated CMakeDeps
find_package(thesias REQUIRED)

add_executable(test_thesias test.c)
target_link_libraries(test_thesias thesias::thesias)

enable_testing()
add_test(NAME test_thesias COMMAND test_thesias)
