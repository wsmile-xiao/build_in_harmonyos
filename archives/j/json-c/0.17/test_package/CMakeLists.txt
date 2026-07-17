cmake_minimum_required(VERSION 3.15)
project(test_json_c C)

# Find the package via Conan-generated CMakeDeps
find_package(json-c REQUIRED)

add_executable(test_json_c test.c)
target_link_libraries(test_json_c json-c::json-c)

enable_testing()
add_test(NAME test_json_c COMMAND test_json_c)
