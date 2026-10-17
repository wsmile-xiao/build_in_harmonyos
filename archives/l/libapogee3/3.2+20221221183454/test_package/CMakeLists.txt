cmake_minimum_required(VERSION 3.15)
project(libapogee3_test CXX)

find_package(libapogee3 REQUIRED CONFIG)

add_executable(test_apogee test_apogee.cpp)
target_link_libraries(test_apogee PRIVATE libapogee3::libapogee3)
