cmake_minimum_required(VERSION 3.15)
project(test_gstreamer1 C)

find_package(gstreamer1.0 REQUIRED)
find_package(glib2 REQUIRED)

add_executable(test_gstreamer1 test.c)
target_link_libraries(test_gstreamer1 gstreamer1.0::gstreamer1.0 glib2::glib2)

enable_testing()
add_test(NAME gstreamer1_test COMMAND test_gstreamer1)
