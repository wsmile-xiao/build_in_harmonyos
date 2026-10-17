cmake_minimum_required(VERSION 3.15)
project(test_libvmime CXX)

find_package(vmime REQUIRED CONFIG)

add_executable(test_libvmime test_libvmime.cpp)
target_link_libraries(test_libvmime vmime::vmime)
