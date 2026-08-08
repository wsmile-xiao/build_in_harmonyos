cmake_minimum_required(VERSION 3.15)
project(gtk_mac_integration_test LANGUAGES C)

find_package(gtk-mac-integration REQUIRED CONFIG)
find_package(glib REQUIRED CONFIG)
add_executable(test_package test_package.c)
target_include_directories(
    test_package
    PRIVATE
        ${GLIB_INCLUDE_DIR}
        ${GLIB_CONFIG_INCLUDE_DIR}
)
target_link_libraries(
    test_package
    PRIVATE
        gtk-mac-integration::gtk-mac-integration
        glib::glib
)

if(TARGET glib::gobject)
    target_link_libraries(test_package PRIVATE glib::gobject)
elseif(TARGET glib::gobject-2.0)
    target_link_libraries(test_package PRIVATE glib::gobject-2.0)
endif()
