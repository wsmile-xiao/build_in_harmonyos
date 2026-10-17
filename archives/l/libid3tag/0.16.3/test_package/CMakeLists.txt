cmake_minimum_required(VERSION 3.15)
project(test_libid3tag C)

# Find the package via Conan-generated CMakeDeps
find_package(libid3tag REQUIRED)
find_package(zlib REQUIRED)

add_executable(test_libid3tag test.c)
target_link_libraries(test_libid3tag libid3tag::libid3tag zlib::zlib)

enable_testing()
add_test(NAME test_libid3tag COMMAND test_libid3tag)
