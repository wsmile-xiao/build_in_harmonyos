cmake_minimum_required(VERSION 3.15)
project(test_libnm C)

find_package(libnm REQUIRED CONFIG)

add_executable(test_libnm test_libnm.c)
target_link_libraries(test_libnm PRIVATE libnm::libnm)
