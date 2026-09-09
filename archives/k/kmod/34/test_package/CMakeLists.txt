cmake_minimum_required(VERSION 3.15)
project(test_kmod C)

# Find the package via Conan-generated CMakeDeps
find_package(kmod REQUIRED)

add_executable(test_kmod test.c)
target_link_libraries(test_kmod kmod::kmod)

enable_testing()
add_test(NAME test_kmod COMMAND test_kmod)
