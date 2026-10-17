cmake_minimum_required(VERSION 3.15)
project(test_libgit2 C)

# Find the package via Conan-generated CMakeDeps
find_package(libgit2 REQUIRED)

add_executable(test_libgit2 test.c)
target_link_libraries(test_libgit2 libgit2::libgit2)

enable_testing()
add_test(NAME test_libgit2 COMMAND test_libgit2)
