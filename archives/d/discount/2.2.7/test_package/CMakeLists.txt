cmake_minimum_required(VERSION 3.15)
project(test_discount C)

# Find the package via Conan-generated CMakeDeps
find_package(discount REQUIRED)

add_executable(test_discount test.c)
target_link_libraries(test_discount discount::discount)

enable_testing()
add_test(NAME test_discount COMMAND test_discount)
