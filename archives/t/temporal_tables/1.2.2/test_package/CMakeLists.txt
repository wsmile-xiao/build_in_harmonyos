cmake_minimum_required(VERSION 3.15)
project(test_temporal_tables C)

# Find the package via Conan-generated CMakeDeps
find_package(temporal_tables REQUIRED)

add_executable(test_temporal_tables test.c)
target_link_libraries(test_temporal_tables temporal_tables::temporal_tables)

enable_testing()
add_test(NAME test_temporal_tables COMMAND test_temporal_tables)
