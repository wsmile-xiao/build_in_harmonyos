cmake_minimum_required(VERSION 3.16)
project(test_xf86_video_dummy C)

add_executable(test_xf86_video_dummy test.c)

# Find the package
find_package(xf86-video-dummy REQUIRED)

# Test verifies that the package's dummy_drv.so can be found
add_test(NAME xf86_video_dummy_test COMMAND test_xf86_video_dummy)
