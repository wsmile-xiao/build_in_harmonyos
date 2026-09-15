cmake_minimum_required(VERSION 3.15)
project(test_quirc C)

# Find the package via Conan-generated CMakeDeps
find_package(quirc REQUIRED)

add_executable(test_quirc test.c)
target_link_libraries(test_quirc quirc::quirc)

enable_testing()
add_test(NAME test_quirc COMMAND test_quirc)
