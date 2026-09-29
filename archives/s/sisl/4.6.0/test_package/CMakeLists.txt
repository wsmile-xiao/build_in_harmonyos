cmake_minimum_required(VERSION 3.15)
project(test_sisl C)

# Find the package via Conan-generated CMakeDeps
find_package(sisl REQUIRED)

add_executable(test_sisl test.c)
target_link_libraries(test_sisl sisl::sisl)

enable_testing()
add_test(NAME test_sisl COMMAND test_sisl)
