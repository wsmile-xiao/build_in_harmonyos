cmake_minimum_required(VERSION 3.15)
project(test_libntruprime LANGUAGES C)

find_package(ntruprime REQUIRED CONFIG)

add_executable(test_ntruprime test_ntruprime.c)
target_link_libraries(test_ntruprime PRIVATE ntruprime::ntruprime)
