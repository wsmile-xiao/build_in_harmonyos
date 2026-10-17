cmake_minimum_required(VERSION 3.15)
project(test_mpdecimal C)

find_package(mpdecimal REQUIRED)

add_executable(test_mpdecimal test_mpdecimal.c)
target_link_libraries(test_mpdecimal PRIVATE mpdecimal::mpdecimal)
