cmake_minimum_required(VERSION 3.15)
project(test_ght C)

find_package(libghthash REQUIRED)

add_executable(test_ght test_ght.c)
target_link_libraries(test_ght libghthash::libghthash)
