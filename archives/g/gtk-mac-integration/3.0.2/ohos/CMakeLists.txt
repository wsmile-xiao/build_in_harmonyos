cmake_minimum_required(VERSION 3.15)
project(gtk_mac_integration_ohos LANGUAGES C)

include(GNUInstallDirs)
find_package(glib REQUIRED CONFIG)

add_library(gtkmacintegration-gtk3 STATIC gtkosxapplication-ohos.c)
target_compile_features(gtkmacintegration-gtk3 PRIVATE c_std_11)
target_compile_definitions(
    gtkmacintegration-gtk3 PUBLIC GTKOSX_HARMONYOS_COMPAT=1
)

target_include_directories(
    gtkmacintegration-gtk3
    PUBLIC
        $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}>
        $<BUILD_INTERFACE:${GLIB_INCLUDE_DIR}>
        $<BUILD_INTERFACE:${GLIB_CONFIG_INCLUDE_DIR}>
        $<INSTALL_INTERFACE:${CMAKE_INSTALL_INCLUDEDIR}>
)
target_link_libraries(
    gtkmacintegration-gtk3
    PUBLIC
        glib::glib
)

# OHPCD's glib/2.84.0 exports one aggregate glib::glib target, while
# component-based GLib recipes export GObject separately. Support both layouts
# so the public GObject dependency is propagated whenever a component exists.
if(TARGET glib::gobject)
    target_link_libraries(
        gtkmacintegration-gtk3
        PUBLIC
            glib::gobject
    )
elseif(TARGET glib::gobject-2.0)
    target_link_libraries(
        gtkmacintegration-gtk3
        PUBLIC
            glib::gobject-2.0
    )
endif()

install(
    TARGETS gtkmacintegration-gtk3
    ARCHIVE DESTINATION ${CMAKE_INSTALL_LIBDIR}
)
install(
    FILES gtkosxapplication.h
    DESTINATION ${CMAKE_INSTALL_INCLUDEDIR}/gtkmacintegration
)
