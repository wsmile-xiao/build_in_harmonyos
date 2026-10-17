cmake_minimum_required(VERSION 3.8)
project(rangev3_test CXX)

find_package(range-v3 REQUIRED)

add_executable(rangev3_test test_package.cpp)
target_link_libraries(rangev3_test PRIVATE range-v3::range-v3)
target_compile_features(rangev3_test PRIVATE cxx_std_17)
