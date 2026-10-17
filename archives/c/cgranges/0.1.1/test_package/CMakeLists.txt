cmake_minimum_required(VERSION 3.15)
project(test_cgranges C)

# Find the package via Conan-generated CMakeDeps
find_package(cgranges REQUIRED)

add_executable(test_cgranges test.c)
target_link_libraries(test_cgranges cgranges::cgranges)

enable_testing()
add_test(NAME test_cgranges COMMAND test_cgranges)
