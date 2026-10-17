cmake_minimum_required(VERSION 3.15)
project(test_box2d C)

# Find the package via Conan-generated CMakeDeps
find_package(box2d REQUIRED)

add_executable(test_box2d test.c)
target_link_libraries(test_box2d box2d::box2d)

enable_testing()
add_test(NAME test_box2d COMMAND test_box2d)
