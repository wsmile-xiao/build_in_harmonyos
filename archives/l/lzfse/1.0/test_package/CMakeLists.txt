cmake_minimum_required(VERSION 3.15)
project(test_lzfse C)

# Find the package via Conan-generated CMakeDeps
find_package(lzfse REQUIRED)

add_executable(test_lzfse test.c)
target_link_libraries(test_lzfse lzfse::lzfse)

enable_testing()
add_test(NAME test_lzfse COMMAND test_lzfse)
