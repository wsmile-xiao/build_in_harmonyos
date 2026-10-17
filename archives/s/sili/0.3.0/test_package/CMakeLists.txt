cmake_minimum_required(VERSION 3.15)
project(test_sili C)

# Find the package via Conan-generated CMakeDeps
find_package(sili REQUIRED)

add_executable(test_sili test.c)
target_link_libraries(test_sili sili::sili)

enable_testing()
add_test(NAME test_sili COMMAND test_sili)
