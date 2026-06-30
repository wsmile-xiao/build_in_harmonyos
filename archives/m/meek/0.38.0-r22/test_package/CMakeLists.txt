cmake_minimum_required(VERSION 3.15)
project(test_meek C)

# Find the package via Conan-generated CMakeDeps
find_package(meek REQUIRED)

add_executable(test_meek test.c)
target_link_libraries(test_meek meek::meek)

enable_testing()
add_test(NAME test_meek COMMAND test_meek)
