cmake_minimum_required(VERSION 3.15)
project(test_gst_plugins_bad10 C)

find_package(gst-plugins-bad1.0 REQUIRED)
find_package(gstreamer REQUIRED)
find_package(glib2 REQUIRED)

add_executable(test_gst_plugins_bad10 test_gst_plugins_bad10.c)
target_link_libraries(test_gst_plugins_bad10
    gst-plugins-bad1.0::gst-plugins-bad1.0
    gstreamer::gstreamer
    glib2::glib2
    ${CMAKE_DL_LIBS})

# End-to-end consumer test (rule12): drives the packaged
# codecparsers library through a real H.264 parsing workflow
# (NAL identification, SPS bitstream decoding and field extraction)
# using the upstream test vector bitstream. This is a pure-function
# library (no GType registry involvement), so the full
# input->parse->assert flow runs end-to-end in one process.
add_executable(test_e2e_consumer test_e2e_consumer.c)
target_compile_definitions(test_e2e_consumer PRIVATE GST_USE_UNSTABLE_API)
target_link_libraries(test_e2e_consumer
    gst-plugins-bad1.0::gst-plugins-bad1.0
    gstreamer::gstreamer
    glib2::glib2
    ${CMAKE_DL_LIBS})

enable_testing()
add_test(NAME gst_plugins_bad10_test COMMAND test_gst_plugins_bad10)
add_test(NAME gst_e2e_consumer_test COMMAND test_e2e_consumer)
