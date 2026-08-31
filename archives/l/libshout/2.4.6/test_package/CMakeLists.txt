cmake_minimum_required(VERSION 3.15)
project(test_libshout C)

# Find the package via Conan-generated CMakeDeps
find_package(libshout REQUIRED)

add_executable(test_libshout test.c)
target_link_libraries(test_libshout libshout::libshout)

enable_testing()
add_test(NAME test_libshout COMMAND test_libshout)
