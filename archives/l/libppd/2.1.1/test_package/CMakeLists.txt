cmake_minimum_required(VERSION 3.15)
project(test_libppd C)

find_package(libppd REQUIRED)
find_package(cups REQUIRED)
find_package(libcupsfilters REQUIRED)

add_executable(test_libppd test_libppd.c)
target_link_libraries(test_libppd PRIVATE libppd::libppd cups::cups libcupsfilters::libcupsfilters)

enable_testing()
add_test(NAME test_libppd COMMAND test_libppd)
