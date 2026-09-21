cmake_minimum_required(VERSION 3.15)
project(test_hyphen C)

# Find the package via Conan-generated CMakeDeps
find_package(hyphen REQUIRED)

add_executable(test_hyphen test.c)
target_link_libraries(test_hyphen hyphen::hyphen)

enable_testing()
add_test(NAME test_hyphen COMMAND test_hyphen)
