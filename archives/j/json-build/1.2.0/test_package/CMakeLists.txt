cmake_minimum_required(VERSION 3.15)
project(test_json-build C)

# Find the package via Conan-generated CMakeDeps
find_package(json-build REQUIRED)

add_executable(test_json-build test.c)
target_link_libraries(test_json-build json-build::json-build)

enable_testing()
add_test(NAME test_json-build COMMAND test_json-build)
