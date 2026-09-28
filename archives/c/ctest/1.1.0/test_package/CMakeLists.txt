cmake_minimum_required(VERSION 3.15)
project(test_ctest C)

# Find the package via Conan-generated CMakeDeps
find_package(ctest REQUIRED)

add_executable(test_ctest test.c)
target_link_libraries(test_ctest ctest::ctest)

enable_testing()
add_test(NAME test_ctest COMMAND test_ctest)
