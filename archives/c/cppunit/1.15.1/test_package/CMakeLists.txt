cmake_minimum_required(VERSION 3.15)
project(test_cppunit CXX)

find_package(cppunit CONFIG REQUIRED)

add_executable(test_cppunit test_cppunit.cpp)
target_compile_features(test_cppunit PRIVATE cxx_std_17)
target_link_libraries(test_cppunit PRIVATE cppunit::cppunit)
