cmake_minimum_required(VERSION 3.15)
project(test_hexagonrpcd C)

find_package(hexagonrpcd REQUIRED)

add_executable(test_hexagonrpcd test.c)
target_link_libraries(test_hexagonrpcd hexagonrpcd::hexagonrpcd)
