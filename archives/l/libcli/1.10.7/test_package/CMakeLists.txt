cmake_minimum_required(VERSION 3.15)

project(test_libcli C)

find_package(libcli CONFIG REQUIRED)

add_executable(test_libcli test_libcli.c)

target_link_libraries(test_libcli PRIVATE libcli::libcli)
