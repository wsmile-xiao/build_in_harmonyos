cmake_minimum_required(VERSION 3.15)
project(test_libeot C)

# Find the package via Conan-generated CMakeDeps
find_package(libeot REQUIRED)

add_executable(libeot_test main.c)
target_link_libraries(libeot_test libeot)

enable_testing()
add_test(NAME libeot_test COMMAND libeot_test)
