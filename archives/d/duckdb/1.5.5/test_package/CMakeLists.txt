cmake_minimum_required(VERSION 3.15)
project(test_duckdb C)

# Find the package via Conan-generated CMakeDeps
find_package(duckdb REQUIRED)

add_executable(test_duckdb test.c)
target_link_libraries(test_duckdb duckdb::duckdb)

enable_testing()
add_test(NAME test_duckdb COMMAND test_duckdb)
