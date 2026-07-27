cmake_minimum_required(VERSION 3.15)
project(test_glib C)

# Find the package via Conan-generated CMakeDeps
find_package(glib REQUIRED)

add_executable(test_glib test.c)
target_link_libraries(test_glib glib::glib)

enable_testing()
add_test(NAME test_glib COMMAND test_glib)
