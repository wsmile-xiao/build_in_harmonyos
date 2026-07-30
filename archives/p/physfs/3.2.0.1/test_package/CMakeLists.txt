cmake_minimum_required(VERSION 3.15)
project(test_physfs C)

# Find the package via Conan-generated CMakeDeps
find_package(physfs REQUIRED)

add_executable(test_physfs test.c)
target_link_libraries(test_physfs physfs::physfs)

enable_testing()
add_test(NAME test_physfs COMMAND test_physfs)
