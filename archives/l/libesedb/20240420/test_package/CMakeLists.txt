cmake_minimum_required(VERSION 3.15)
project(test_libesedb C)

# Find the package via Conan-generated CMakeDeps
find_package(libesedb REQUIRED)

add_executable(test_libesedb test.c)
target_link_libraries(test_libesedb libesedb::libesedb)

enable_testing()
add_test(NAME test_libesedb COMMAND test_libesedb)
