cmake_minimum_required(VERSION 3.15)
project(test_composefs C)

# Find the package via Conan-generated CMakeDeps
find_package(composefs REQUIRED)

add_executable(test_composefs test.c)
target_link_libraries(test_composefs composefs::composefs)

enable_testing()
add_test(NAME test_composefs COMMAND test_composefs)
