cmake_minimum_required(VERSION 3.15)
project(test_lzo C)

# Find the package via Conan-generated CMakeDeps
find_package(lzo REQUIRED)

add_executable(test_lzo test.c)
target_link_libraries(test_lzo lzo::lzo)

enable_testing()
add_test(NAME test_lzo COMMAND test_lzo)
