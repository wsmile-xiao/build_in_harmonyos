cmake_minimum_required(VERSION 3.19)
project(test_nvtx CXX)

find_package(nvtx3 REQUIRED)

add_executable(test_nvtx test_nvtx.cpp)
target_link_libraries(test_nvtx PRIVATE nvtx3::nvtx3-cpp nvtx3::nvtxw3-loader)