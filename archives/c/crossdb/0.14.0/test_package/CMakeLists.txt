cmake_minimum_required(VERSION 3.15)
project(test_crossdb C)

# Find the package via Conan-generated CMakeDeps
find_package(crossdb REQUIRED)

add_executable(test_crossdb test.c)
target_link_libraries(test_crossdb crossdb::crossdb)

enable_testing()
add_test(NAME test_crossdb COMMAND test_crossdb)
