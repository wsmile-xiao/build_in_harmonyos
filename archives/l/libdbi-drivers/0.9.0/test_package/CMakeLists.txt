cmake_minimum_required(VERSION 3.15)
project(libdbi_drivers_test C)

find_package(libdbi CONFIG REQUIRED)
find_package(libdbi-drivers CONFIG REQUIRED)

add_executable(test_libdbi_drivers test_libdbi_drivers.c)
target_link_libraries(test_libdbi_drivers PRIVATE
    libdbi::libdbi
    libdbi-drivers::libdbi-drivers
)
