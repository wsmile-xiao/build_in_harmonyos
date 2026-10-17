cmake_minimum_required(VERSION 3.15)
project(test_maskedvbyte C)

# Find the package via Conan-generated CMakeDeps
find_package(maskedvbyte REQUIRED)

add_executable(test_maskedvbyte test.c)
target_link_libraries(test_maskedvbyte maskedvbyte::maskedvbyte)

enable_testing()
add_test(NAME test_maskedvbyte COMMAND test_maskedvbyte)
