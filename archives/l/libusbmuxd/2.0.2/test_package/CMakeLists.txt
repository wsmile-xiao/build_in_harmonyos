cmake_minimum_required(VERSION 3.15)
project(test_libusbmuxd C)

# Find the package via Conan-generated CMakeDeps
find_package(libusbmuxd REQUIRED)

add_executable(test_libusbmuxd test.c)
target_link_libraries(test_libusbmuxd libusbmuxd::libusbmuxd)

enable_testing()
add_test(NAME test_libusbmuxd COMMAND test_libusbmuxd)
