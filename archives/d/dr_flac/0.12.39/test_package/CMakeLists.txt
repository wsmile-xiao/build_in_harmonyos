cmake_minimum_required(VERSION 3.15)
project(test_package C)

find_package(dr_flac REQUIRED)

add_executable(test_dr_flac test_dr_flac.c)
target_link_libraries(test_dr_flac PRIVATE dr_flac::dr_flac)
# dr_flac is a single-header library: consumers must define DR_FLAC_IMPLEMENTATION
# in exactly one translation unit to compile the implementation. The test vector
# header lives next to the test source.
target_compile_definitions(test_dr_flac PRIVATE DR_FLAC_IMPLEMENTATION)
