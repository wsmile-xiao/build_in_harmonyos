cmake_minimum_required(VERSION 3.15)
project(test_stc C)

# STC 头文件要求 C11
set(CMAKE_C_STANDARD 11)
set(CMAKE_C_STANDARD_REQUIRED ON)

# Find the package via Conan-generated CMakeDeps
find_package(stc REQUIRED)

add_executable(test_stc test.c)
target_link_libraries(test_stc stc::stc)

enable_testing()
add_test(NAME test_stc COMMAND test_stc)
