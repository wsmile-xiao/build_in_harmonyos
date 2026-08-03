cmake_minimum_required(VERSION 3.15)
project(test_blisp C)

# Find the package via Conan-generated CMakeDeps.
find_package(blisp REQUIRED)

add_executable(test_blisp test_blisp.c)
target_link_libraries(test_blisp blisp::blisp)
