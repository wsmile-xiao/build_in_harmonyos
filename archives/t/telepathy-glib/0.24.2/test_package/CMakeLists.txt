cmake_minimum_required(VERSION 3.15)
project(test_telepathy_glib C)

find_package(glib CONFIG REQUIRED)
find_package(dbus CONFIG REQUIRED)
find_package(dbus-glib CONFIG REQUIRED)
find_package(telepathy-glib CONFIG REQUIRED)

add_executable(test_telepathy_glib test_telepathy_glib.c)
target_link_libraries(test_telepathy_glib PRIVATE
    telepathy-glib::telepathy-glib
    glib::glib-2.0
    glib::gio-2.0
    dbus-glib::dbus-glib
    dbus::dbus)
