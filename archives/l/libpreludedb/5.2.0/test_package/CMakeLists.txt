cmake_minimum_required(VERSION 3.10)
project(test_libpreludedb C)

# Find the package via Conan-generated CMakeDeps
find_package(libpreludedb REQUIRED)

add_executable(test_libpreludedb test.c)
target_link_libraries(test_libpreludedb libpreludedb::libpreludedb)

enable_testing()
add_test(NAME test_libpreludedb COMMAND test_libpreludedb)
