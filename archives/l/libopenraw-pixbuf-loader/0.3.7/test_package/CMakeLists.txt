cmake_minimum_required(VERSION 3.15)
project(test_libopenraw_pixbuf_loader C)

# The test dlopen()s the packaged libopenraw_pixbuf.so module and calls its
# fill_info() / fill_vtable() entry points.  It needs the real gdk-pixbuf
# backend headers (for the GdkPixbufFormat / GdkPixbufModule structs) but no
# link-time dependency on the loader module itself — the module is loaded at
# runtime.
find_package(gdk-pixbuf REQUIRED)

add_executable(test_openraw_pixbuf_loader test.c)
target_link_libraries(test_openraw_pixbuf_loader
    PRIVATE
        gdk-pixbuf::gdk-pixbuf
        ${CMAKE_DL_LIBS}
)

enable_testing()
add_test(NAME test_openraw_pixbuf_loader COMMAND test_openraw_pixbuf_loader)
