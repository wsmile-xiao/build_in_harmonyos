cmake_minimum_required(VERSION 3.15)
project(test_cjson C)

# Find the package via Conan-generated CMakeDeps
find_package(c-json REQUIRED)

add_executable(test_cjson test.c)
target_link_libraries(test_cjson c-json::c-json)

enable_testing()
add_test(NAME test_cjson COMMAND test_cjson)
