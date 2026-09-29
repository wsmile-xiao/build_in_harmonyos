cmake_minimum_required(VERSION 3.15)
project(test_zeek C)

# Find the package via Conan-generated CMakeDeps
find_package(zeek REQUIRED)

add_executable(test_zeek test.c)
target_link_libraries(test_zeek zeek::zeek)

enable_testing()
add_test(NAME test_zeek COMMAND test_zeek)
