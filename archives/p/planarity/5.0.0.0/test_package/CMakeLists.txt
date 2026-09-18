cmake_minimum_required(VERSION 3.15)
project(test_planarity C)

# Find the package via Conan-generated CMakeDeps
find_package(planarity REQUIRED)

add_executable(test_planarity test_planarity.c)
target_link_libraries(test_planarity planarity::planarity)

enable_testing()
add_test(NAME test_planarity_api COMMAND test_planarity)
