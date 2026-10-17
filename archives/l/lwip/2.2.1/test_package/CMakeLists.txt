cmake_minimum_required(VERSION 3.15)
project(test_lwip C)

# Find the package via Conan-generated CMakeDeps
find_package(lwip REQUIRED)

add_executable(test_lwip test.c)
target_link_libraries(test_lwip lwip::lwip)

enable_testing()
add_test(NAME test_lwip COMMAND test_lwip)