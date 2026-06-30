cmake_minimum_required(VERSION 3.15)
project(test_zxc C)

# Find the package via Conan-generated CMakeDeps
find_package(zxc REQUIRED)

add_executable(test_zxc test.c)
target_link_libraries(test_zxc zxc::zxc)

enable_testing()
add_test(NAME test_zxc COMMAND test_zxc)
