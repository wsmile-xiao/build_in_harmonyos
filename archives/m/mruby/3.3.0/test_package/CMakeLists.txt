cmake_minimum_required(VERSION 3.15)
project(test_mruby C)

# Find the package via Conan-generated CMakeDeps
find_package(mruby REQUIRED)

add_executable(test_mruby test.c)
target_link_libraries(test_mruby mruby::mruby)

enable_testing()
add_test(NAME test_mruby COMMAND test_mruby)
