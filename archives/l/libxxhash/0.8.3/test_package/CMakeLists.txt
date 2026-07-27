cmake_minimum_required(VERSION 3.15)
project(test_libxxhash C)

# Find the package via Conan-generated CMakeDeps
find_package(libxxhash CONFIG REQUIRED)

add_executable(test_libxxhash test.c)
target_link_libraries(test_libxxhash libxxhash::libxxhash)

enable_testing()
add_test(NAME test_libxxhash COMMAND test_libxxhash)
