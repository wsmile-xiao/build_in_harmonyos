cmake_minimum_required(VERSION 3.15)
project(test_libplist C)

# Find the package via Conan-generated CMakeDeps
find_package(libplist-2.0 REQUIRED)

add_executable(test_libplist test.c)
target_link_libraries(test_libplist libplist::libplist)

enable_testing()
add_test(NAME test_libplist COMMAND test_libplist)
