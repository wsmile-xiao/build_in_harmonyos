cmake_minimum_required(VERSION 3.15)
project(test_xcb_util_wm C)

if(DEFINED CMAKE_FIND_ROOT_PATH_MODE_PACKAGE)
    set(CMAKE_FIND_ROOT_PATH_MODE_PACKAGE BOTH)
endif()

find_package(xcb-util-wm REQUIRED)
find_package(libxcb REQUIRED)

add_executable(test_xcb_util_wm test.c)
# Link the consumed package through its CMakeDeps target, and libxcb
# explicitly: the test source includes <xcb/xcb.h> and <xcb/xcb_icccm.h>,
# whose include directories are carried by the libxcb / xorgproto targets.
target_link_libraries(test_xcb_util_wm PRIVATE
    xcb-util-wm::xcb-util-wm
    libxcb::libxcb)

enable_testing()
add_test(NAME test_xcb_util_wm COMMAND test_xcb_util_wm)
