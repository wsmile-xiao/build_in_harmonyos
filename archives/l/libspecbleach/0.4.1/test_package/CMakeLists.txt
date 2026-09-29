cmake_minimum_required(VERSION 3.15)
project(test_libspecbleach C)

# Find the package via Conan-generated CMakeDeps
find_package(libspecbleach REQUIRED)

add_executable(test_libspecbleach test.c)
target_link_libraries(test_libspecbleach libspecbleach::libspecbleach)

enable_testing()
add_test(NAME test_libspecbleach COMMAND test_libspecbleach)
