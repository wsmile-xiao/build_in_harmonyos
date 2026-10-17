cmake_minimum_required(VERSION 3.15)
project(test_libqrcodegen C)

# Find the package via Conan-generated CMakeDeps
find_package(libqrcodegen REQUIRED)

add_executable(test_libqrcodegen test.c)
target_link_libraries(test_libqrcodegen libqrcodegen::libqrcodegen)

enable_testing()
add_test(NAME test_libqrcodegen COMMAND test_libqrcodegen)
