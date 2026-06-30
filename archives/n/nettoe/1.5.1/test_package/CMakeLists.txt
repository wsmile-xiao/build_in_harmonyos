cmake_minimum_required(VERSION 3.15)
project(test_nettoe C)

# Find the package via Conan-generated CMakeDeps
find_package(nettoe REQUIRED)

add_executable(test_nettoe test.c)
target_link_libraries(test_nettoe nettoe::nettoe)

enable_testing()
add_test(NAME test_nettoe COMMAND test_nettoe)
