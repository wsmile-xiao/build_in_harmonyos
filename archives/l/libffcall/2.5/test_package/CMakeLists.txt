cmake_minimum_required(VERSION 3.15)
project(test_libffcall C)

# Find the package via Conan-generated CMakeDeps
find_package(libffcall REQUIRED)

add_executable(test_libffcall test.c)
target_link_libraries(test_libffcall libffcall::libffcall)

enable_testing()
add_test(NAME test_libffcall COMMAND test_libffcall)
