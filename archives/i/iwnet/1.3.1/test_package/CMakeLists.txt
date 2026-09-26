cmake_minimum_required(VERSION 3.15)
project(test_iwnet C)

# Find the package via Conan-generated CMakeDeps
find_package(iwnet REQUIRED)

add_executable(test_iwnet test.c)
target_link_libraries(test_iwnet iwnet::iwnet)

enable_testing()
add_test(NAME test_iwnet COMMAND test_iwnet)
