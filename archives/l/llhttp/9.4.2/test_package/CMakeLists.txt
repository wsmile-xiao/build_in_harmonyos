cmake_minimum_required(VERSION 3.15)
project(test_llhttp C)

# Find the package via Conan-generated CMakeDeps
find_package(llhttp REQUIRED)

add_executable(test_llhttp test.c)
target_link_libraries(test_llhttp llhttp::llhttp)

enable_testing()
add_test(NAME test_llhttp COMMAND test_llhttp)
