cmake_minimum_required(VERSION 3.15)
project(test_cbitset C)

# Find the package via Conan-generated CMakeDeps
find_package(cbitset REQUIRED)

add_executable(test_cbitset test.c)
target_link_libraries(test_cbitset cbitset::cbitset)

enable_testing()
add_test(NAME test_cbitset COMMAND test_cbitset)
