cmake_minimum_required(VERSION 3.15)
project(test_arena-allocator C)

# Find the package via Conan-generated CMakeDeps
find_package(arena-allocator REQUIRED)

add_executable(test_arena-allocator test.c)
target_link_libraries(test_arena-allocator arena-allocator::arena-allocator)

enable_testing()
add_test(NAME test_arena-allocator COMMAND test_arena-allocator)
