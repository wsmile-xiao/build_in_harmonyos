cmake_minimum_required(VERSION 3.15)
project(test_gst_libav C)

# Find the plugin path from the gst-libav dependency
# At conan test time, the package is installed to a conan cache folder
# We use a custom approach: the test_package conanfile passes the path

add_executable(test_gst_libav test.c)
target_link_libraries(test_gst_libav ${CMAKE_DL_LIBS})

enable_testing()
add_test(NAME gst_libav_test COMMAND test_gst_libav
    $ENV{GST_LIBAV_PLUGIN_PATH}
)
