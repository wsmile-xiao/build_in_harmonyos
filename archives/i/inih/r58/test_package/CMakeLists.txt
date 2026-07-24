cmake_minimum_required(VERSION 3.15)
project(test_inih C)

# Find the package via Conan-generated CMakeDeps
find_package(inih REQUIRED)

add_executable(test_inih test_inih.c)
target_link_libraries(test_inih inih::inih)

enable_testing()
add_test(NAME test_inih COMMAND test_inih)
