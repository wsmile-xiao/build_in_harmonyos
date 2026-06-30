cmake_minimum_required(VERSION 3.15)
project(test_umka-lang C)

# Find the package via Conan-generated CMakeDeps
find_package(umka-lang REQUIRED)

add_executable(test_umka-lang test.c)
target_link_libraries(test_umka-lang umka-lang::umka-lang)

enable_testing()
add_test(NAME test_umka-lang COMMAND test_umka-lang)
