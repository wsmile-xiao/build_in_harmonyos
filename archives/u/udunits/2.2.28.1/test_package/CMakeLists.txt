cmake_minimum_required(VERSION 3.15)
project(test_udunits C)

# Find the package via Conan-generated CMakeDeps
find_package(udunits REQUIRED)

add_executable(test_udunits test.c)
target_link_libraries(test_udunits udunits::udunits)

enable_testing()
add_test(NAME test_udunits COMMAND test_udunits)
