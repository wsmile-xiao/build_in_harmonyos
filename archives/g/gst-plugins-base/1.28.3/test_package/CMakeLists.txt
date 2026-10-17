cmake_minimum_required(VERSION 3.15)
project(test_gst_plugins_base C)

find_package(gst-plugins-base REQUIRED)
find_package(gstreamer REQUIRED)
find_package(glib2 REQUIRED)

add_executable(test_gst_plugins_base test.c)
target_link_libraries(test_gst_plugins_base gst-plugins-base::gst-plugins-base gstreamer::gstreamer glib2::glib2)

enable_testing()
add_test(NAME gst_plugins_base_test COMMAND test_gst_plugins_base)
