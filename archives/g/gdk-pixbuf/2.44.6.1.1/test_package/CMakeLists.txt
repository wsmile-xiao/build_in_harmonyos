cmake_minimum_required(VERSION 3.15)
project(test_gdk-pixbuf C)

# Find the package via Conan-generated CMakeDeps (cmake_file_name = gdk-pixbuf-2.0)
find_package(gdk-pixbuf-2.0 REQUIRED)

add_executable(test_gdk-pixbuf test.c)
target_link_libraries(test_gdk-pixbuf gdk-pixbuf-2.0::gdk-pixbuf-2.0)

enable_testing()
add_test(NAME test_gdk-pixbuf COMMAND test_gdk-pixbuf)
