cmake_minimum_required(VERSION 3.15)
project(test_libmcrypt C)

find_package(libmcrypt REQUIRED CONFIG)

add_executable(test_libmcrypt test_libmcrypt.c)
target_link_libraries(test_libmcrypt PRIVATE libmcrypt::libmcrypt)
