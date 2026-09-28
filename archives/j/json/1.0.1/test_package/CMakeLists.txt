cmake_minimum_required(VERSION 3.15)
project(test_json C)

# Find the package via Conan-generated CMakeDeps
find_package(json REQUIRED)

add_executable(test_json test.c)
target_link_libraries(test_json json::json)

enable_testing()
add_test(NAME test_json COMMAND test_json)
