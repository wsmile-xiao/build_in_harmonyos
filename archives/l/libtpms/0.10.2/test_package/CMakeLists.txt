cmake_minimum_required(VERSION 3.15)
project(test_libtpms C)

# Find the package via Conan-generated CMakeDeps
find_package(libtpms REQUIRED)

add_executable(test_libtpms test.c)
target_link_libraries(test_libtpms libtpms::libtpms)

enable_testing()
add_test(NAME test_libtpms COMMAND test_libtpms)
