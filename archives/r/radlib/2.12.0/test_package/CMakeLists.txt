cmake_minimum_required(VERSION 3.15)
project(test_radlib C)

# Find the package via Conan-generated CMakeDeps
find_package(radlib REQUIRED)

add_executable(test_radlib test_radlib.c)
target_link_libraries(test_radlib radlib::radlib)

enable_testing()
add_test(NAME test_radlib COMMAND test_radlib)
