cmake_minimum_required(VERSION 3.15)
project(test_dbus_test_runner C)

find_package(glib CONFIG REQUIRED)
find_package(dbus-glib CONFIG REQUIRED)
find_package(dbustest CONFIG REQUIRED)

add_executable(test_dbus_test_runner test_dbus_test_runner.c)
target_link_libraries(test_dbus_test_runner PRIVATE
    dbustest::dbustest
    glib::glib-2.0
    glib::gio-2.0
    dbus-glib::dbus-glib)
