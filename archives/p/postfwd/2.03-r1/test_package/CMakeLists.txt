cmake_minimum_required(VERSION 3.15)
project(test_postfwd C)

# Find the package via Conan-generated CMakeDeps
find_package(postfwd REQUIRED)

add_executable(test_postfwd test.c)
target_link_libraries(test_postfwd postfwd::postfwd)

enable_testing()
add_test(NAME test_postfwd COMMAND test_postfwd)
