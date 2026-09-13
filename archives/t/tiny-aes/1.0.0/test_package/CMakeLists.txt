cmake_minimum_required(VERSION 3.15)
project(test_tiny_aes C)

find_package(tiny-aes REQUIRED)

add_executable(test_tiny_aes test_tiny_aes.c)
target_link_libraries(test_tiny_aes tiny-aes::tiny-aes)

enable_testing()
add_test(NAME test_tiny_aes COMMAND test_tiny_aes)
