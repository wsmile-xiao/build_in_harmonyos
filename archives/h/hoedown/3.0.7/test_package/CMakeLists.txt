cmake_minimum_required(VERSION 3.15)
project(test_hoedown C)

# Find the package via Conan-generated CMakeDeps
find_package(hoedown REQUIRED)

add_executable(test_hoedown test.c)
target_link_libraries(test_hoedown hoedown::hoedown)

enable_testing()
add_test(NAME test_hoedown COMMAND test_hoedown)
