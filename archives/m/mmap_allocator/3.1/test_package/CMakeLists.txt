cmake_minimum_required(VERSION 3.15)
project(test_mmap_allocator CXX)

# Find the package via Conan-generated CMakeDeps
find_package(mmap_allocator REQUIRED)

add_executable(test_mmap_allocator test.cpp)
target_link_libraries(test_mmap_allocator mmap_allocator::mmap_allocator)

enable_testing()
add_test(NAME test_mmap_allocator COMMAND test_mmap_allocator)
