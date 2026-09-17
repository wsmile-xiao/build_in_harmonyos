cmake_minimum_required(VERSION 3.15)
project(test_unixcw C)

# Find the package via Conan-generated CMakeDeps
find_package(libcw REQUIRED)

add_executable(test_unixcw test_unixcw.c)
target_link_libraries(test_unixcw libcw::libcw)

enable_testing()
add_test(NAME test_unixcw COMMAND test_unixcw)
