cmake_minimum_required(VERSION 3.15)

project(test_libmurmurhash C)

find_package(libmurmurhash CONFIG REQUIRED)

add_executable(test_libmurmurhash test.c)

target_link_libraries(test_libmurmurhash PRIVATE libmurmurhash::libmurmurhash)
