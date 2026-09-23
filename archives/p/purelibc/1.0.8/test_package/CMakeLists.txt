cmake_minimum_required(VERSION 3.15)
project(purelibc_test LANGUAGES C)

find_package(purelibc CONFIG REQUIRED)

add_executable(purelibc_capture_test purelibc_capture_test.c)
target_link_libraries(purelibc_capture_test PRIVATE purelibc::purelibc)

add_executable(purelibc_parse_mode_test purelibc_parse_mode_test.c)
target_link_libraries(purelibc_parse_mode_test PRIVATE purelibc::purelibc)
