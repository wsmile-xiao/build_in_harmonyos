cmake_minimum_required(VERSION 3.15)
project(test_xdg-ninja C)

# Find the package via Conan-generated CMakeDeps
find_package(xdg-ninja REQUIRED)

add_executable(test_xdg-ninja test.c)
target_link_libraries(test_xdg-ninja xdg-ninja::xdg-ninja)

enable_testing()
add_test(NAME test_xdg-ninja COMMAND test_xdg-ninja)
