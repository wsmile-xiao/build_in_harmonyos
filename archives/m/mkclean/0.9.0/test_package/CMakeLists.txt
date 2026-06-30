cmake_minimum_required(VERSION 3.15)
project(test_mkclean C)

# Find the package via Conan-generated CMakeDeps
find_package(mkclean REQUIRED)

# mkclean is a terminal tool, test by running the binary
add_executable(test_mkclean test.c)

enable_testing()
add_test(NAME test_mkclean COMMAND test_mkclean)
