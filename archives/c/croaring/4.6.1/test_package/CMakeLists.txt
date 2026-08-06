cmake_minimum_required(VERSION 3.15)
project(test_croaring C)

# Find the package via Conan-generated CMakeDeps
find_package(croaring REQUIRED)

add_executable(test_croaring test.c)
target_link_libraries(test_croaring croaring::croaring)

enable_testing()
add_test(NAME test_croaring COMMAND test_croaring)
