cmake_minimum_required(VERSION 3.15)
project(test_libindi C)

# Find the package via Conan-generated CMakeDeps
find_package(libindi REQUIRED)

add_executable(test_libindi test.c)
target_link_libraries(test_libindi libindi::libindi)

enable_testing()
add_test(NAME test_libindi COMMAND test_libindi)
