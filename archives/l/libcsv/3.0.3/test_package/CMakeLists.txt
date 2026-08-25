cmake_minimum_required(VERSION 3.15)

project(test_libcsv C)

find_package(libcsv CONFIG REQUIRED)

add_executable(test_libcsv test.c)

target_link_libraries(test_libcsv PRIVATE libcsv::libcsv)
