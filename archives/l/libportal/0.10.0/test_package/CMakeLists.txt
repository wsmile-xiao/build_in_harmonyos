cmake_minimum_required(VERSION 3.15)
project(test_libportal C)

find_package(libportal REQUIRED)

add_executable(test_libportal test_libportal.c)
target_link_libraries(test_libportal PRIVATE libportal::libportal)
