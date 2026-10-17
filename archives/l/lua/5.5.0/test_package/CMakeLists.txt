cmake_minimum_required(VERSION 3.15)
project(test_lua C)

# Find the package via Conan-generated CMakeDeps
find_package(lua REQUIRED)

add_executable(test_lua test.c)
target_link_libraries(test_lua lua::lua)

enable_testing()
add_test(NAME test_lua COMMAND test_lua)
