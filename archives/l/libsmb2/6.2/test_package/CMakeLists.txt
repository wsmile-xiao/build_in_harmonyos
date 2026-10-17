cmake_minimum_required(VERSION 3.15)
project(test_libsmb2 C)

# Find the package via Conan-generated CMakeDeps
find_package(libsmb2 REQUIRED)

add_executable(test_libsmb2 test_libsmb2.c)
target_link_libraries(test_libsmb2 libsmb2::libsmb2)

enable_testing()
add_test(NAME test_libsmb2 COMMAND test_libsmb2)
