cmake_minimum_required(VERSION 3.15)
project(test_pkgconf C)

find_package(pkgconf CONFIG REQUIRED)

add_executable(test_pkgconf test.c)
target_link_libraries(test_pkgconf PRIVATE pkgconf::pkgconf)
