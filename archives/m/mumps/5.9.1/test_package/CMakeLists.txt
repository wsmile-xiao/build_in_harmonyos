cmake_minimum_required(VERSION 3.15)
project(test_mumps C)

# Find the package via Conan-generated CMakeDeps
find_package(mumps REQUIRED)

add_executable(test_mumps test.c)
target_link_libraries(test_mumps mumps::mumps m)

enable_testing()
add_test(NAME test_mumps COMMAND test_mumps)
