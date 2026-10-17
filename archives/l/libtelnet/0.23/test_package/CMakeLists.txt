cmake_minimum_required(VERSION 3.15)
project(test_libtelnet C)

# Find the package via Conan-generated CMakeDeps
find_package(libtelnet REQUIRED)

add_executable(test_libtelnet test.c)
target_link_libraries(test_libtelnet libtelnet::libtelnet)

enable_testing()
add_test(NAME test_libtelnet COMMAND test_libtelnet)
