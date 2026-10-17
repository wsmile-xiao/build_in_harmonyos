cmake_minimum_required(VERSION 3.15)
project(test_fastlz C)

# Find the package via Conan-generated CMakeDeps
find_package(fastlz REQUIRED)

add_executable(test_fastlz test.c)
target_link_libraries(test_fastlz fastlz::fastlz)

enable_testing()
add_test(NAME test_fastlz COMMAND test_fastlz)