cmake_minimum_required(VERSION 3.15)
project(test_packcc C)

# Find the package via Conan-generated CMakeDeps
find_package(packcc REQUIRED)

add_executable(test_packcc test.c)
target_link_libraries(test_packcc packcc::packcc)

enable_testing()
add_test(NAME test_packcc COMMAND test_packcc)
