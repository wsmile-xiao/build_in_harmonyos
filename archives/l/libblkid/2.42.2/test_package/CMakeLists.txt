cmake_minimum_required(VERSION 3.15)
project(test_libblkid C)

find_package(blkid REQUIRED CONFIG)

add_executable(test_blkid_api test_blkid.c)
target_link_libraries(test_blkid_api PRIVATE blkid::blkid)
