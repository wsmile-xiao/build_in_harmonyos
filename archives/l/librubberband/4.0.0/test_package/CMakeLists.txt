cmake_minimum_required(VERSION 3.16)
project(test_librubberband C)

find_package(rubberband REQUIRED)

add_executable(test_librubberband test_package.c)
target_link_libraries(test_librubberband PRIVATE rubberband::rubberband m)
