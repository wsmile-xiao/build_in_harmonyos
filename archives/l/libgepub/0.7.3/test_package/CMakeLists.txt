cmake_minimum_required(VERSION 3.15)
project(test_libgepub C)

# Find the packages via Conan-generated CMakeDeps files
# (the glib recipe names its CMake package "GLib": GLib::GLib etc.).
find_package(libgepub-0.7 CONFIG REQUIRED)
find_package(GLib CONFIG REQUIRED)

add_executable(test_libgepub test.c)
target_link_libraries(test_libgepub libgepub-0.7::libgepub-0.7 GLib::GLib GLib::GObject GLib::Gio)

# Headless port of upstream tests/test-gepub.c 7 TEST() cases (no GTK/webkit).
add_executable(upstream_headless upstream_headless.c)
target_link_libraries(upstream_headless libgepub-0.7::libgepub-0.7 GLib::GLib GLib::GObject GLib::Gio)

enable_testing()
add_test(NAME test_libgepub COMMAND test_libgepub book.epub)
add_test(NAME upstream_headless COMMAND upstream_headless book.epub)
