cmake_minimum_required(VERSION 3.15)
project(test_cparsec C)

# Find the package via Conan-generated CMakeDeps
find_package(cparsec REQUIRED)

add_executable(test_cparsec test.c)
target_link_libraries(test_cparsec cparsec::cparsec)

enable_testing()
add_test(NAME test_cparsec COMMAND test_cparsec)
