cmake_minimum_required(VERSION 3.15)
project(test_lz4 C)

# Find the package via Conan-generated CMakeDeps
find_package(lz4 REQUIRED)

add_executable(test_lz4 test.c)
target_link_libraries(test_lz4 lz4::lz4)

# Path B consumer cases: frame API + dictionary API (v1.10.0 stable symbols)
add_executable(test_lz4_consumer test_lz4_consumer.c)
target_link_libraries(test_lz4_consumer lz4::lz4)

enable_testing()
add_test(NAME test_lz4 COMMAND test_lz4)
add_test(NAME test_lz4_consumer COMMAND test_lz4_consumer)
