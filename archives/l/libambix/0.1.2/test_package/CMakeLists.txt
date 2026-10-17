cmake_minimum_required(VERSION 3.15)
project(test_libambix LANGUAGES C)

find_package(libambix CONFIG REQUIRED)

add_executable(test_libambix test.c)
target_link_libraries(test_libambix PRIVATE libambix::libambix)
