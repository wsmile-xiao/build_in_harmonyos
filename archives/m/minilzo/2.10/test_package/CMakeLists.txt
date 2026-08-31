cmake_minimum_required(VERSION 3.15)
project(test_minilzo C)

# Find the package via Conan-generated CMakeDeps
find_package(minilzo REQUIRED)

add_executable(test_minilzo test.c)
target_link_libraries(test_minilzo minilzo::minilzo)

enable_testing()
add_test(NAME test_minilzo COMMAND test_minilzo)
