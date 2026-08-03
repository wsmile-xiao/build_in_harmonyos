cmake_minimum_required(VERSION 3.15)
project(libvorbis_test_package LANGUAGES C)

find_package(Vorbis REQUIRED CONFIG)

add_executable(test_libvorbis test_libvorbis.c)
target_link_libraries(
    test_libvorbis
    PRIVATE
        Vorbis::vorbis
        Vorbis::vorbisenc
        Vorbis::vorbisfile
)

add_executable(
    libvorbis_upstream_test
    upstream/test.c
    upstream/util.c
    upstream/write_read.c
)
target_include_directories(
    libvorbis_upstream_test
    PRIVATE
        upstream
)
target_link_libraries(
    libvorbis_upstream_test
    PRIVATE
        Vorbis::vorbis
        Vorbis::vorbisenc
)
