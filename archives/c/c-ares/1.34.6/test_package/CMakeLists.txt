cmake_minimum_required(VERSION 3.15)
project(test_c-ares C)

# Find the package via Conan-generated CMakeDeps
find_package(c-ares REQUIRED)

add_executable(test_c-ares test.c)
target_link_libraries(test_c-ares c-ares::c-ares)

enable_testing()
add_test(NAME test_c-ares COMMAND test_c-ares)
