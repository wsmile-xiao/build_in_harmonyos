cmake_minimum_required(VERSION 3.15)
project(test_vte C)

# Conan's CMakeDeps does not propagate transitive include dirs for
# harfbuzz (harfbuzz_INCLUDE_DIRS_RELEASE is empty), so pango's
# #include <hb.h> fails.  We use pkg-config manually to get the full
# include + link flags for vte and all its transitive deps.
find_package(PkgConfig REQUIRED)
pkg_check_modules(VTE REQUIRED IMPORTED_TARGET vte-2.91)

add_executable(test_vte test.c)
target_link_libraries(test_vte PkgConfig::VTE)

enable_testing()
add_test(NAME test_vte COMMAND test_vte)
