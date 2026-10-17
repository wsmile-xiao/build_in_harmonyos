cmake_minimum_required(VERSION 3.15)
project(test_libaio C)

# Find the package via Conan-generated CMakeDeps
find_package(libaio REQUIRED)

add_executable(test_libaio test.c)
target_link_libraries(test_libaio libaio::libaio)

enable_testing()
add_test(NAME test_libaio COMMAND test_libaio)
