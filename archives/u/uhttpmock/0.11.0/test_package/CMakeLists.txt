cmake_minimum_required(VERSION 3.15)
project(test_uhttpmock C)

# Find the package via Conan-generated CMakeDeps
# (cmake_file_name=libuhttpmock-1.0).
# Only link libuhttpmock-1.0 itself: glib/gobject/soup symbols resolve
# through its NEEDED chain (single GObject copy doctrine, see notes.md).
find_package(libuhttpmock-1.0 CONFIG REQUIRED)

add_executable(test_uhttpmock test_uhttpmock.c)
target_link_libraries(test_uhttpmock PRIVATE libuhttpmock-1.0::libuhttpmock-1.0)

enable_testing()
add_test(NAME test_uhttpmock COMMAND test_uhttpmock)
