cmake_minimum_required(VERSION 3.15)
project(test_cimg CXX)

find_package(CImg REQUIRED)

add_executable(test_cimg test_cimg.cpp)
target_link_libraries(test_cimg PRIVATE CImg::CImg)
set_target_properties(test_cimg PROPERTIES CXX_STANDARD 17)
