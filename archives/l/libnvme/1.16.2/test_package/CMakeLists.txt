cmake_minimum_required(VERSION 3.10)
project(test_libnvme C)

find_package(libnvme REQUIRED)

add_executable(test_libnvme test_libnvme.c)
target_link_libraries(test_libnvme PRIVATE libnvme::libnvme)
