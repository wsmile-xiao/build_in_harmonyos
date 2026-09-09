cmake_minimum_required(VERSION 3.5)
project(test_tabulate CXX)

# Find the package via Conan-generated CMakeDeps
find_package(tabulate REQUIRED)

add_executable(test_tabulate test.cpp)
target_link_libraries(test_tabulate tabulate::tabulate)

enable_testing()
add_test(NAME test_tabulate COMMAND test_tabulate)