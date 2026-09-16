cmake_minimum_required(VERSION 3.15)
project(test_bglibs C)

# Find the package via Conan-generated CMakeDeps
find_package(bglibs REQUIRED)

add_executable(test_bglibs test.c)
target_link_libraries(test_bglibs bglibs::bglibs)

enable_testing()
add_test(NAME test_bglibs COMMAND test_bglibs)
