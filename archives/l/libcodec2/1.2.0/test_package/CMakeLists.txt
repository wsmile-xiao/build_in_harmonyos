cmake_minimum_required(VERSION 3.15)
project(test_codec2 C)

# Find the package via Conan-generated CMakeDeps
find_package(codec2 REQUIRED)

add_executable(test_codec2 test.c)
target_link_libraries(test_codec2 codec2::codec2)

enable_testing()
add_test(NAME test_codec2 COMMAND test_codec2)
