cmake_minimum_required(VERSION 3.15)
project(test_gsound C)

# Find the package via Conan-generated CMakeDeps (cmake_file_name=gsound).
# Only link gsound: glib/gobject/libcanberra symbols resolve through
# libgsound.so's NEEDED chain (single GObject copy doctrine).
find_package(gsound CONFIG REQUIRED)

add_executable(test_gsound test_gsound.c)
target_link_libraries(test_gsound PRIVATE gsound::gsound)

enable_testing()
add_test(NAME test_gsound COMMAND test_gsound)
