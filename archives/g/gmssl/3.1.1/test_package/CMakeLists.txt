cmake_minimum_required(VERSION 3.15)
project(test_gmssl C)

# Find the package via Conan-generated CMakeDeps
find_package(gmssl REQUIRED)

add_executable(test_gmssl test.c)
target_link_libraries(test_gmssl gmssl::gmssl)

enable_testing()
add_test(NAME test_gmssl COMMAND test_gmssl)
