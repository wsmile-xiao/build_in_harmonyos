cmake_minimum_required(VERSION 3.15)
project(test_libvo-aacenc C)

# Find the package via Conan-generated CMakeDeps
find_package(libvo-aacenc REQUIRED)

add_executable(test_libvo-aacenc test.c)
target_link_libraries(test_libvo-aacenc libvo-aacenc::libvo-aacenc)

enable_testing()
add_test(NAME test_libvo-aacenc COMMAND test_libvo-aacenc)
