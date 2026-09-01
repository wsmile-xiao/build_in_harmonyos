cmake_minimum_required(VERSION 3.15)
project(test_msitools C)

# Find packages via Conan-generated CMakeDeps
find_package(msitools REQUIRED)
find_package(GLib REQUIRED)

add_executable(test_msitools test.c)
target_link_libraries(test_msitools msitools::msitools glib::glib)

enable_testing()
add_test(NAME test_msitools COMMAND test_msitools)
