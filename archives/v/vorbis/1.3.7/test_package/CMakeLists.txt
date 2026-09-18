cmake_minimum_required(VERSION 3.15)
project(vorbis_test_package LANGUAGES C)

find_package(Vorbis REQUIRED CONFIG)

add_executable(test_vorbis test_vorbis.c)
target_link_libraries(
    test_vorbis
    PRIVATE
        Vorbis::vorbis
        Vorbis::vorbisenc
        Vorbis::vorbisfile
)

add_executable(
    vorbis_upstream_test
    upstream/test.c
    upstream/util.c
    upstream/write_read.c
)
target_include_directories(
    vorbis_upstream_test
    PRIVATE
        upstream
)
target_link_libraries(
    vorbis_upstream_test
    PRIVATE
        Vorbis::vorbis
        Vorbis::vorbisenc
)
