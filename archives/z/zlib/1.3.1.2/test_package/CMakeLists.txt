cmake_minimum_required(VERSION 3.15)
project(test_zlib C)

# Find the package via Conan-generated CMakeDeps
find_package(zlib REQUIRED)

add_executable(test_zlib test.c)
target_link_libraries(test_zlib zlib::zlib)

enable_testing()
add_test(NAME test_zlib COMMAND test_zlib)
