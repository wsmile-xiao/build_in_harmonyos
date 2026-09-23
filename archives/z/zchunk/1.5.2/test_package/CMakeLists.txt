cmake_minimum_required(VERSION 3.15)
project(test_zchunk C)

# Find the package via Conan-generated CMakeDeps
find_package(zchunk REQUIRED)

add_executable(test_zchunk test.c)
target_link_libraries(test_zchunk zchunk::zchunk)

enable_testing()
add_test(NAME test_zchunk COMMAND test_zchunk)
