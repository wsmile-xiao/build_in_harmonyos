cmake_minimum_required(VERSION 3.15)
project(test_sundials C)

# Find the package via Conan-generated CMakeDeps
find_package(sundials REQUIRED)

add_executable(test_sundials test.c)
target_link_libraries(test_sundials sundials::sundials)

enable_testing()
add_test(NAME test_sundials COMMAND test_sundials)
