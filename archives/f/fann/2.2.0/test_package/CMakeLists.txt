cmake_minimum_required(VERSION 3.15)
project(test_fann C)

# Find the package via Conan-generated CMakeDeps
find_package(fann REQUIRED)

add_executable(test_fann test.c)
target_link_libraries(test_fann fann::fann)

enable_testing()
add_test(NAME test_fann COMMAND test_fann)
