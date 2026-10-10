cmake_minimum_required(VERSION 3.15)
project(clapper_test LANGUAGES C)

# The clapper public headers (<clapper/clapper.h> -> clapper-enum-types.h)
# include GLib/GObject and GStreamer headers transitively, so those packages
# must be found and linked too. Same pattern as the gstreamer / gst-plugins-base
# test_packages (verified gate-passing consumers).
find_package(clapper CONFIG REQUIRED)
find_package(glib2 REQUIRED)
find_package(gstreamer REQUIRED)
find_package(gst-plugins-base REQUIRED)
add_executable(test_clapper test.c)
target_link_libraries(test_clapper PRIVATE clapper::clapper glib2::glib2 gstreamer::gstreamer gst-plugins-base::gst-plugins-base)
