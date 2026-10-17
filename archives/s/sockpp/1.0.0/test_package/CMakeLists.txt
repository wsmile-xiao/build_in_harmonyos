cmake_minimum_required(VERSION 3.15)
project(test_sockpp CXX)

find_package(sockpp REQUIRED)

add_executable(test_sockpp test_sockpp.cpp)
target_compile_features(test_sockpp PRIVATE cxx_std_14)
target_link_libraries(test_sockpp PRIVATE sockpp::sockpp)
