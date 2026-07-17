cmake_minimum_required(VERSION 3.15)
project(test_jansson C)

# Find the package via Conan-generated CMakeDeps
find_package(jansson REQUIRED)

add_executable(test_jansson test.c)
target_link_libraries(test_jansson jansson::jansson)

enable_testing()
add_test(NAME test_jansson COMMAND test_jansson)
