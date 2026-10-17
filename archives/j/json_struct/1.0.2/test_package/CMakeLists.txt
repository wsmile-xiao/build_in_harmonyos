cmake_minimum_required(VERSION 3.15)
project(test_json_struct CXX)

# Find the package via Conan-generated CMakeDeps
find_package(json_struct REQUIRED)

add_executable(test_json_struct test_package.cpp)
target_link_libraries(test_json_struct json_struct::json_struct)

enable_testing()
add_test(NAME test_json_struct COMMAND test_json_struct)