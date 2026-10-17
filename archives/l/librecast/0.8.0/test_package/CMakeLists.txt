cmake_minimum_required(VERSION 3.15)
project(test_librecast C)

# Find the package via Conan-generated CMakeDeps
find_package(librecast REQUIRED)

add_executable(test_librecast test.c)
target_link_libraries(test_librecast librecast::librecast)

enable_testing()
add_test(NAME test_librecast COMMAND test_librecast)
