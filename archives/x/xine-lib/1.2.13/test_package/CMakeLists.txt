cmake_minimum_required(VERSION 3.15)
project(test_xine-lib C)

# Package metadata comes from the Conan-generated CMakeDeps files.
find_package(xine-lib REQUIRED)

add_executable(test_xine-lib test.c)
target_link_libraries(test_xine-lib xine-lib::xine-lib)

enable_testing()
add_test(NAME test_xine-lib COMMAND test_xine-lib)
