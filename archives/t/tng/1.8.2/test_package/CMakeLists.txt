cmake_minimum_required(VERSION 3.15)
project(test_tng C)

# Find the package via Conan-generated CMakeDeps
find_package(tng_io REQUIRED)

add_executable(test_tng test.c)
target_link_libraries(test_tng tng_io::tng_io)

enable_testing()
add_test(NAME test_tng COMMAND test_tng)
