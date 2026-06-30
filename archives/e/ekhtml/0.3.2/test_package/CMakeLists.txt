cmake_minimum_required(VERSION 3.15)
project(test_ekhtml C)

# Find the package via Conan-generated CMakeDeps
find_package(ekhtml REQUIRED)

add_executable(test_ekhtml test.c)
target_link_libraries(test_ekhtml ekhtml::ekhtml)

enable_testing()
add_test(NAME test_ekhtml COMMAND test_ekhtml)
