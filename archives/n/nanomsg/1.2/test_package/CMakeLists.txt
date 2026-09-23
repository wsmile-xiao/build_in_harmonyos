cmake_minimum_required(VERSION 3.15)
project(test_nanomsg C)

# Find the package via Conan-generated CMakeDeps
find_package(nanomsg REQUIRED)

add_executable(test_nanomsg test.c)
target_link_libraries(test_nanomsg nanomsg::nanomsg)

enable_testing()
add_test(NAME test_nanomsg COMMAND test_nanomsg)
