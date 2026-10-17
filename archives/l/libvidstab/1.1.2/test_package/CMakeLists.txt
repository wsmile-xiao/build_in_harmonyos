cmake_minimum_required(VERSION 3.15)
project(test_vidstab C)

find_package(vidstab REQUIRED CONFIG)

add_executable(test_vidstab test_vidstab.c)
target_link_libraries(test_vidstab PRIVATE vidstab::vidstab)

enable_testing()
add_test(NAME test_vidstab COMMAND test_vidstab)
