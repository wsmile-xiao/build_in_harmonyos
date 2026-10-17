cmake_minimum_required(VERSION 3.15)
project(test_liblinear CXX)

find_package(liblinear REQUIRED)

add_executable(test_liblinear test_liblinear.cpp)
target_link_libraries(test_liblinear PRIVATE liblinear::liblinear)
