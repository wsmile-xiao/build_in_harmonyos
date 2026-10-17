cmake_minimum_required(VERSION 3.15)
project(test_liboauth C)

# Find the package via Conan-generated CMakeDeps
find_package(liboauth REQUIRED)

add_executable(test_liboauth test.c)
target_link_libraries(test_liboauth liboauth::liboauth)

enable_testing()
add_test(NAME test_liboauth COMMAND test_liboauth)
