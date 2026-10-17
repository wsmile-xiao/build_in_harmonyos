cmake_minimum_required(VERSION 3.15)
project(test_umka C)

# Find the package via Conan-generated CMakeDeps
find_package(umka-lang REQUIRED)

add_executable(test_umka test.c)
target_link_libraries(test_umka umka-lang::umka-lang)

enable_testing()
add_test(NAME test_umka COMMAND test_umka)
