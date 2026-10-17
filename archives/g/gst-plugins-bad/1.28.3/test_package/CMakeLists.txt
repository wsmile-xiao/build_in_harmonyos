cmake_minimum_required(VERSION 3.15)
project(test_gst_plugins_bad C)

find_package(gst-plugins-bad REQUIRED)
find_package(gstreamer REQUIRED)
find_package(glib2 REQUIRED)

add_executable(test_gst_plugins_bad test_gst_plugins_bad.c)
target_link_libraries(test_gst_plugins_bad
    gst-plugins-bad::gst-plugins-bad
    gstreamer::gstreamer
    glib2::glib2
    ${CMAKE_DL_LIBS})

enable_testing()
add_test(NAME gst_plugins_bad_test COMMAND test_gst_plugins_bad)
