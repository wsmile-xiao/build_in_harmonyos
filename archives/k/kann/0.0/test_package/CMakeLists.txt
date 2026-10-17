cmake_minimum_required(VERSION 3.15)
project(test_kann C)

# Find the package via Conan-generated CMakeDeps
find_package(kann REQUIRED)

add_executable(test_kann test.c)
target_link_libraries(test_kann kann::kann)

enable_testing()
add_test(NAME test_kann COMMAND test_kann)
