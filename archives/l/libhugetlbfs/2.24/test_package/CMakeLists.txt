cmake_minimum_required(VERSION 3.15)
project(test_libhugetlbfs C)

# Find the package via Conan-generated CMakeDeps
find_package(libhugetlbfs REQUIRED)

add_executable(test_libhugetlbfs test.c)
target_link_libraries(test_libhugetlbfs libhugetlbfs::libhugetlbfs)

enable_testing()
add_test(NAME test_libhugetlbfs COMMAND test_libhugetlbfs)
