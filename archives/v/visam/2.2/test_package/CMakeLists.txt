cmake_minimum_required(VERSION 3.15)
project(visam_test C)

find_package(visam CONFIG REQUIRED)

add_executable(visam_consumer main.c)
target_link_libraries(visam_consumer PRIVATE visam::visam)

enable_testing()
add_test(NAME visam_consumer COMMAND visam_consumer)
