cmake_minimum_required(VERSION 3.15)
project(test_plutovg C)
set(CMAKE_C_STANDARD 11)
set(CMAKE_C_STANDARD_REQUIRED ON)

# Find the package via Conan-generated CMakeDeps.
find_package(plutovg CONFIG REQUIRED)

add_executable(test_plutovg test.c)
target_link_libraries(test_plutovg plutovg::plutovg)

enable_testing()
add_test(NAME test_plutovg COMMAND test_plutovg)
