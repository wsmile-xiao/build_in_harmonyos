cmake_minimum_required(VERSION 3.15)
project(test_metis C)

# Find the package via Conan-generated CMakeDeps
find_package(metis REQUIRED)

add_executable(test_metis test.c)
target_link_libraries(test_metis metis::metis)

enable_testing()
add_test(NAME test_metis COMMAND test_metis)
