cmake_minimum_required(VERSION 3.15)
project(test_libevdev C)

# Find the package via Conan-generated CMakeDeps
find_package(libevdev REQUIRED)

add_executable(test_libevdev test.c)
target_link_libraries(test_libevdev libevdev::libevdev)

enable_testing()
add_test(NAME test_libevdev COMMAND test_libevdev)
