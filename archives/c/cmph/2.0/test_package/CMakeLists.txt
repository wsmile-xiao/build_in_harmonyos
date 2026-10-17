cmake_minimum_required(VERSION 3.15)
project(test_cmph C)

# Find the package via Conan-generated CMakeDeps
find_package(cmph REQUIRED)

add_executable(test_cmph test.c)
target_link_libraries(test_cmph cmph::cmph)

enable_testing()
add_test(NAME test_cmph COMMAND test_cmph)
