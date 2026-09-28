cmake_minimum_required(VERSION 3.15)
project(test_lasem_render C)

# Find the package via Conan-generated CMakeDeps. The dependency headers
# (cairo.h / hb.h / glib-object.h) are pulled in by lasem's public headers,
# and lld requires the explicit libraries on the link line for every symbol
# the test's macro-expanded code references (g_object_unref from
# g_object_unref calls, g_type_check_instance_is_a from the LSM_IS_* type
# checks) — link them by name using the generator-provided lib directories.
find_package(lasem REQUIRED)
find_package(cairo REQUIRED)
find_package(harfbuzz REQUIRED)
find_package(glib REQUIRED)

add_executable(test_lasem_render test_lasem_render.c)
target_link_directories(test_lasem_render PRIVATE
    ${cairo_LIB_DIRS_RELEASE}
    ${glib_LIB_DIRS_RELEASE}
    ${harfbuzz_LIB_DIRS_RELEASE})
target_link_libraries(test_lasem_render
    lasem-render::lasem-render
    harfbuzz::harfbuzz
    cairo
    gobject-2.0
    glib-2.0)

enable_testing()
add_test(NAME test_lasem_render COMMAND test_lasem_render)
