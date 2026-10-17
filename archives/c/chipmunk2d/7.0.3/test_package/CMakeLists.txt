cmake_minimum_required(VERSION 3.15)
project(test_chipmunk2d C)

# Find the package via Conan-generated CMakeDeps
find_package(chipmunk2d REQUIRED)

add_executable(test_chipmunk2d test.c)
target_link_libraries(test_chipmunk2d chipmunk2d::chipmunk2d)

enable_testing()
add_test(NAME test_chipmunk2d COMMAND test_chipmunk2d)
