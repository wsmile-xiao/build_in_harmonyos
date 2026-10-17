cmake_minimum_required(VERSION 3.16)
project(knighttime_test LANGUAGES CXX)

find_package(KNightTime REQUIRED)

add_executable(test_knighttime test_knighttime.cpp)
target_link_libraries(test_knighttime PRIVATE KNightTime)
target_compile_features(test_knighttime PRIVATE cxx_std_20)
