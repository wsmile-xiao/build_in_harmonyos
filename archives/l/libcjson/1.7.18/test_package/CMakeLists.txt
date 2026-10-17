cmake_minimum_required(VERSION 3.15)
project(test_libcjson C)

# Find the package via Conan-generated CMakeDeps
find_package(libcjson REQUIRED)

add_executable(test_libcjson test_libcjson.c)
target_link_libraries(test_libcjson libcjson::libcjson)

enable_testing()
add_test(NAME test_libcjson COMMAND test_libcjson)