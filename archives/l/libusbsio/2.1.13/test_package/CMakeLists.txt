cmake_minimum_required(VERSION 3.15)
project(test_libusbsio C)

find_package(libusbsio REQUIRED)

add_executable(test_libusbsio test_libusbsio.c)
target_link_libraries(test_libusbsio PRIVATE libusbsio::libusbsio)

add_executable(test_upstream_suite test_upstream_suite.c)
target_link_libraries(test_upstream_suite PRIVATE libusbsio::libusbsio)
