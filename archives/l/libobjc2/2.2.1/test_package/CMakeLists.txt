cmake_minimum_required(VERSION 3.15)
project(test_libobjc2 C)

# Find the package via Conan-generated CMakeDeps
find_package(libobjc2 REQUIRED)

add_executable(test_libobjc2 test.c)
target_link_libraries(test_libobjc2 libobjc2::libobjc2)

enable_testing()
add_test(NAME test_libobjc2 COMMAND test_libobjc2)
