cmake_minimum_required(VERSION 3.15)
project(test_webp_pixbuf_loader C)

# The test uses dlopen to load the pixbufloader-webp shared module
# and calls its fill_info() entry point.  No link-time dependency on
# the package is needed — the module is loaded at runtime.
add_executable(test_webp_pixbuf_loader test.c)
target_link_libraries(test_webp_pixbuf_loader ${CMAKE_DL_LIBS})

enable_testing()
add_test(NAME test_webp_pixbuf_loader COMMAND test_webp_pixbuf_loader)
