cmake_minimum_required(VERSION 3.15)

project(test_libcidr C)

find_package(libcidr CONFIG REQUIRED)

add_executable(test_libcidr test_libcidr.c)

target_link_libraries(test_libcidr PRIVATE libcidr::libcidr)
