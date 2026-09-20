cmake_minimum_required(VERSION 3.16)
project(test_xrootd LANGUAGES CXX)

find_package(xrootd REQUIRED)

add_executable(test_xrootd test_xrootd.cpp)
target_compile_features(test_xrootd PRIVATE cxx_std_17)
target_link_libraries(test_xrootd PRIVATE xrootd::XrdCl xrootd::XrdUtils)
