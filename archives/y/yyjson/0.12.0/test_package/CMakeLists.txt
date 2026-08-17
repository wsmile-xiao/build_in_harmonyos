cmake_minimum_required(VERSION 3.15)
project(test_yyjson C)

# Find the package via Conan-generated CMakeDeps
find_package(yyjson REQUIRED)

add_executable(test_yyjson test.c)
target_link_libraries(test_yyjson yyjson::yyjson)

enable_testing()
add_test(NAME test_yyjson COMMAND test_yyjson)
