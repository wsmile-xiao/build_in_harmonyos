cmake_minimum_required(VERSION 3.15)
project(test_libjodycode C)

# Find the package via Conan-generated CMakeDeps
find_package(libjodycode REQUIRED)

add_executable(test_libjodycode test.c)
target_link_libraries(test_libjodycode libjodycode::libjodycode)

enable_testing()
add_test(NAME test_libjodycode COMMAND test_libjodycode)
