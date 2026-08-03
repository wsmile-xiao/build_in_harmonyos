cmake_minimum_required(VERSION 3.15)
project(test_cgns C)

# Find the package via Conan-generated CMakeDeps
find_package(cgns REQUIRED)

add_executable(test_cgns test_package.c)
target_link_libraries(test_cgns cgns::cgns)

enable_testing()
add_test(NAME test_cgns COMMAND test_cgns)
