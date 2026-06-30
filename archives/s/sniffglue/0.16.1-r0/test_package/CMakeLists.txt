cmake_minimum_required(VERSION 3.15)
project(test_sniffglue C)

# Find the package via Conan-generated CMakeDeps
find_package(sniffglue REQUIRED)

add_executable(test_sniffglue test.c)
target_link_libraries(test_sniffglue sniffglue::sniffglue)

enable_testing()
add_test(NAME test_sniffglue COMMAND test_sniffglue)
