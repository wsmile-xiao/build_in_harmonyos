cmake_minimum_required(VERSION 3.15)
project(test_libudev-zero C)

# Find the package via Conan-generated CMakeDeps
find_package(libudev-zero REQUIRED)

add_executable(test_libudev-zero test.c)
target_link_libraries(test_libudev-zero libudev-zero::libudev-zero)

enable_testing()
add_test(NAME test_libudev-zero COMMAND test_libudev-zero)
