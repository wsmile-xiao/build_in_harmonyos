cmake_minimum_required(VERSION 3.15)
project(test_libreplaygain C)

# Find the package via Conan-generated CMakeDeps
find_package(libreplaygain REQUIRED)

add_executable(test_libreplaygain test.c)
target_link_libraries(test_libreplaygain libreplaygain::libreplaygain)

enable_testing()
add_test(NAME test_libreplaygain COMMAND test_libreplaygain)
