cmake_minimum_required(VERSION 3.15)
project(slop_consumer LANGUAGES CXX)

find_package(slop CONFIG REQUIRED)

add_executable(test_slop_api test_slop_api.cpp)
target_link_libraries(test_slop_api PRIVATE slop::slop)
target_compile_features(test_slop_api PRIVATE cxx_std_17)
