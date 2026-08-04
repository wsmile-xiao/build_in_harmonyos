cmake_minimum_required(VERSION 3.5)
project(test_zziplib LANGUAGES C)

find_package(zziplib REQUIRED CONFIG)

add_executable(test_zziplib test.c)
target_link_libraries(test_zziplib PRIVATE zziplib::zziplib)