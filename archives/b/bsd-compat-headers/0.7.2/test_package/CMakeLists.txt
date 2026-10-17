cmake_minimum_required(VERSION 3.15)
project(test_bsd_compat_headers C)

find_package(bsd-compat-headers CONFIG REQUIRED)

add_executable(test_bsd_compat_headers src/main.c)
target_link_libraries(test_bsd_compat_headers PRIVATE bsd-compat-headers::bsd-compat-headers)
