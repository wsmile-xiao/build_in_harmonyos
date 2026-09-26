cmake_minimum_required(VERSION 3.15)
project(test_tiny_aes_c LANGUAGES CXX)

find_package(tiny-aes-c CONFIG REQUIRED)

add_executable(test_tiny_aes_c test_tiny_aes_c.cpp)
target_link_libraries(test_tiny_aes_c PRIVATE tiny-aes-c::tiny-aes-c)
target_compile_features(test_tiny_aes_c PRIVATE cxx_std_17)
target_compile_options(
    test_tiny_aes_c
    PRIVATE
        -Wall
        -Wextra
        -Wpedantic
        -Werror
        -Wno-error=unused-command-line-argument
)
