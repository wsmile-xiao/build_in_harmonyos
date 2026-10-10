cmake_minimum_required(VERSION 3.15)
project(test_libxosd C)

find_package(libxosd CONFIG REQUIRED)

add_executable(test_libxosd test.c)
target_link_libraries(test_libxosd PRIVATE libxosd::libxosd)
