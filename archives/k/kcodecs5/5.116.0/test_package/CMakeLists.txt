cmake_minimum_required(VERSION 3.15)
project(test_kcodecs5 CXX)

find_package(KF5Codecs REQUIRED)
find_package(Qt5Core REQUIRED)

add_executable(test_kcodecs5 test.cpp)
target_link_libraries(test_kcodecs5 KF5::Codecs Qt5::Core)
