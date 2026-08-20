cmake_minimum_required(VERSION 3.15)
project(test_libsndfile LANGUAGES C)

find_package(SndFile CONFIG REQUIRED)

add_executable(test_libsndfile test_libsndfile.c)
target_link_libraries(test_libsndfile PRIVATE SndFile::sndfile)
