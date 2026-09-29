cmake_minimum_required(VERSION 3.15)
project(test_libinstpatch C)

# Find the package via Conan-generated CMakeDeps
find_package(libinstpatch REQUIRED)

# glib/gobject/gthread headers are found via pkg-config (glib's CMakeDeps
# metadata exposes no include dirs; upstream also uses pkg_check_modules).
find_package(PkgConfig REQUIRED)
pkg_check_modules(GLIB_DEPS REQUIRED glib-2.0 gobject-2.0 gthread-2.0)

add_executable(test_libinstpatch test.c)
target_link_libraries(test_libinstpatch libinstpatch::libinstpatch)
target_include_directories(test_libinstpatch PRIVATE ${GLIB_DEPS_INCLUDE_DIRS})
target_link_libraries(test_libinstpatch ${GLIB_DEPS_LIBRARIES})

enable_testing()
add_test(NAME test_libinstpatch COMMAND test_libinstpatch)
