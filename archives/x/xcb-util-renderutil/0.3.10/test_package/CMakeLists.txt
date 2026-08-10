cmake_minimum_required(VERSION 3.15)
project(test_xcb_util_renderutil C)

# OHOS user toolchain sets CMAKE_FIND_ROOT_PATH_MODE_PACKAGE=ONLY,
# which prevents find_package() from searching CMAKE_PREFIX_PATH.
# Override to BOTH so the conan generators directory is searched.
if(DEFINED CMAKE_FIND_ROOT_PATH_MODE_PACKAGE)
    set(CMAKE_FIND_ROOT_PATH_MODE_PACKAGE BOTH)
endif()

find_package(xcb-util-renderutil REQUIRED)

add_executable(test_xcb_util_renderutil test.c)
target_link_libraries(test_xcb_util_renderutil PRIVATE xcb-util-renderutil::xcb-util-renderutil)

enable_testing()
add_test(NAME test_xcb_util_renderutil COMMAND test_xcb_util_renderutil)
