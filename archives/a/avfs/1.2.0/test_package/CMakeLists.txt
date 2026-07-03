cmake_minimum_required(VERSION 3.15)
project(test_avfs C)

# Find the package via Conan-generated CMakeDeps
find_package(avfs REQUIRED)

add_executable(test_avfs test.c)
target_link_libraries(test_avfs avfs::avfs)

enable_testing()
add_test(NAME test_avfs COMMAND test_avfs)
