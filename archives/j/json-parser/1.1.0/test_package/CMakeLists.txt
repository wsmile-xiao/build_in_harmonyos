cmake_minimum_required(VERSION 3.15)
project(test_json-parser C)

# Find the package via Conan-generated CMakeDeps
find_package(json-parser REQUIRED)

add_executable(test_json-parser test.c)
target_link_libraries(test_json-parser json-parser::json-parser)

enable_testing()
add_test(NAME test_json-parser COMMAND test_json-parser)
