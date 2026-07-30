cmake_minimum_required(VERSION 3.15)
project(test_mp4v2 CXX)

find_package(mp4v2 REQUIRED)

add_executable(test_mp4v2 test.cpp)
target_link_libraries(test_mp4v2 mp4v2::mp4v2)
target_compile_features(test_mp4v2 PRIVATE cxx_std_17)
