cmake_minimum_required(VERSION 3.15)
project(test_libaco C)

# Find the package via Conan-generated CMakeDeps
find_package(libaco REQUIRED)

add_executable(test_libaco test.c)
target_link_libraries(test_libaco libaco::libaco)

enable_testing()
add_test(NAME test_libaco COMMAND test_libaco)
