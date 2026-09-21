cmake_minimum_required(VERSION 3.15)
project(test_apk C)

find_package(apk CONFIG REQUIRED)

add_executable(test_apk test_apk.c)
target_link_libraries(test_apk PRIVATE apk::apk)
