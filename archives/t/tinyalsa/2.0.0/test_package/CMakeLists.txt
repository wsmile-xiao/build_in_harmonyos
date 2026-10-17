cmake_minimum_required(VERSION 3.15)
project(test_tinyalsa C)

# Find the package via Conan-generated CMakeDeps
find_package(tinyalsa REQUIRED)

add_executable(test_tinyalsa test.c)
target_link_libraries(test_tinyalsa tinyalsa::tinyalsa)

enable_testing()
add_test(NAME test_tinyalsa COMMAND test_tinyalsa)
