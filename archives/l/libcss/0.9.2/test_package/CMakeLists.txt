cmake_minimum_required(VERSION 3.15)
project(libcss_consumer_test C)

# Find libcss via Conan-generated CMakeDeps (libwapcaplet 0.4.3
# test_package precedent: find_package + LibCSS::css target).
# libwapcaplet is found too: test.c includes its header directly
# (the node-query handler works with lwc_string interned strings).
find_package(LibCSS REQUIRED)
find_package(LibWapcaplet REQUIRED)

add_executable(libcss_consumer_test test.c)
target_link_libraries(libcss_consumer_test PRIVATE LibCSS::css LibWapcaplet::wapcaplet)
