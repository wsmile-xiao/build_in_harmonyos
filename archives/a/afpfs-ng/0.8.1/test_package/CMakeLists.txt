cmake_minimum_required(VERSION 3.15)
project(test_afpfs-ng C)

# Find the package via Conan-generated CMakeDeps
find_package(afpfs-ng REQUIRED)

add_executable(test_afpfs-ng test.c)
target_link_libraries(test_afpfs-ng afpfs-ng::afpfs-ng)

enable_testing()
add_test(NAME test_afpfs-ng COMMAND test_afpfs-ng)
