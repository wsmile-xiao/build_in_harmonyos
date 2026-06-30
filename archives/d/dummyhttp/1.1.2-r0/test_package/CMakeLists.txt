cmake_minimum_required(VERSION 3.15)
project(test_dummyhttp C)

# Find the package via Conan-generated CMakeDeps
find_package(dummyhttp REQUIRED)

add_executable(test_dummyhttp test.c)
target_link_libraries(test_dummyhttp dummyhttp::dummyhttp)

enable_testing()
add_test(NAME test_dummyhttp COMMAND test_dummyhttp)
