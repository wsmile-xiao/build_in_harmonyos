cmake_minimum_required(VERSION 3.15)
project(test_berkeley-db5 C)

# Find the package via Conan-generated CMakeDeps
find_package(berkeley-db5 REQUIRED)

add_executable(test_berkeley-db5 test.c)
target_link_libraries(test_berkeley-db5 berkeley-db5::berkeley-db5)

enable_testing()
add_test(NAME test_berkeley-db5 COMMAND test_berkeley-db5)
