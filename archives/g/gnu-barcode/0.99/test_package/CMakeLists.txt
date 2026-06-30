cmake_minimum_required(VERSION 3.15)
project(test_gnu-barcode C)

# Find the package via Conan-generated CMakeDeps
find_package(gnu-barcode REQUIRED)

add_executable(test_gnu-barcode test.c)
target_link_libraries(test_gnu-barcode gnu-barcode::gnu-barcode)

enable_testing()
add_test(NAME test_gnu-barcode COMMAND test_gnu-barcode)
