cmake_minimum_required(VERSION 3.15)
project(test_aes-stream C)

# Find the package via Conan-generated CMakeDeps
find_package(aes-stream REQUIRED)

add_executable(test_aes-stream test.c)
target_link_libraries(test_aes-stream aes-stream::aes-stream)

enable_testing()
add_test(NAME test_aes-stream COMMAND test_aes-stream)
