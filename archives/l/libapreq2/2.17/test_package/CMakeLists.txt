cmake_minimum_required(VERSION 3.15)
project(test_apreq2 C)

find_package(libapreq2 CONFIG REQUIRED)
find_package(apr CONFIG REQUIRED)
find_package(expat CONFIG REQUIRED)

add_executable(test_apreq2 test_apreq2.c)
target_link_libraries(test_apreq2 PRIVATE libapreq2::libapreq2)
