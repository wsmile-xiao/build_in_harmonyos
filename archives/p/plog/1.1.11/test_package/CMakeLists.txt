cmake_minimum_required(VERSION 3.15)
project(test_plog LANGUAGES CXX)

find_package(plog CONFIG REQUIRED)

add_executable(test_plog test_plog.cpp)
target_compile_features(test_plog PRIVATE cxx_std_11)
target_link_libraries(test_plog PRIVATE plog::plog)
