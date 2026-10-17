cmake_minimum_required(VERSION 3.15)
project(test_lvm2 C)

# Find the package via Conan-generated CMakeDeps
find_package(lvm2 REQUIRED)

add_executable(test_lvm2 test.c)
target_link_libraries(test_lvm2 lvm2::lvm2)

enable_testing()
add_test(NAME test_lvm2 COMMAND test_lvm2)
