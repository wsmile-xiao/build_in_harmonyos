cmake_minimum_required(VERSION 3.15)
project(test_pmars C)

# Find the package via Conan-generated CMakeDeps
find_package(pmars REQUIRED)

add_executable(test_pmars test.c)
target_link_libraries(test_pmars pmars::pmars)

enable_testing()
add_test(NAME test_pmars COMMAND test_pmars)
