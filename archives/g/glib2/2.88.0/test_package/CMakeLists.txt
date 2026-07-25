cmake_minimum_required(VERSION 3.15)
project(test_glib2 C)

# Find the package via Conan-generated CMakeDeps.
find_package(glib2 REQUIRED)

add_executable(test_glib2 test_glib.c)
target_link_libraries(test_glib2 glib2::glib2)

enable_testing()
add_test(NAME test_glib2 COMMAND test_glib2)
