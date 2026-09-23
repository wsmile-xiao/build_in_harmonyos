cmake_minimum_required(VERSION 3.15)
project(test_vo-amrwbenc C)

# Find the package via Conan-generated CMakeDeps
find_package(vo-amrwbenc REQUIRED)

add_executable(test_vo-amrwbenc test.c)
target_link_libraries(test_vo-amrwbenc vo-amrwbenc::vo-amrwbenc)

enable_testing()
add_test(NAME test_vo-amrwbenc COMMAND test_vo-amrwbenc)
