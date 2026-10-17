cmake_minimum_required(VERSION 3.15)
project(test_package C)

# Find the package via Conan-generated CMakeDeps
find_package(libnids REQUIRED)
find_package(libpcap REQUIRED)

add_executable(test_package test_package.c)
target_link_libraries(test_package libnids::libnids libpcap::libpcap)
