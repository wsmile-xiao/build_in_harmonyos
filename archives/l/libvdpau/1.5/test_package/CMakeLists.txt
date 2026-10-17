cmake_minimum_required(VERSION 3.15)
project(test_libvdpau C)

find_package(vdpau REQUIRED)

add_executable(test_libvdpau test.c)
target_link_libraries(test_libvdpau PRIVATE vdpau::vdpau)
