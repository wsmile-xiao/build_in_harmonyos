cmake_minimum_required(VERSION 3.15)
project(test_liblzma C)

# Find the package via Conan-generated CMakeDeps
find_package(liblzma REQUIRED)

add_executable(test_liblzma test.c)
target_link_libraries(test_liblzma liblzma::liblzma)

enable_testing()
add_test(NAME test_liblzma COMMAND test_liblzma)
