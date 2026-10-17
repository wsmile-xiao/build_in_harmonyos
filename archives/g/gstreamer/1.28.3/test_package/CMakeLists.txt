cmake_minimum_required(VERSION 3.15)
project(test_gstreamer C)

find_package(gstreamer REQUIRED)
find_package(glib2 REQUIRED)

add_executable(test_gstreamer test.c)
target_link_libraries(test_gstreamer gstreamer::gstreamer glib2::glib2)

enable_testing()
add_test(NAME gstreamer_test COMMAND test_gstreamer)
