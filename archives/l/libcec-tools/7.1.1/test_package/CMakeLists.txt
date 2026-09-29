cmake_minimum_required(VERSION 3.15)
project(test_libcec LANGUAGES CXX)

find_package(libcec REQUIRED)

add_executable(test_libcec test_libcec.cpp)
target_link_libraries(test_libcec PRIVATE libcec::libcec)
