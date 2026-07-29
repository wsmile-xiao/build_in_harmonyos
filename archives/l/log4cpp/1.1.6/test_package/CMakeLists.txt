cmake_minimum_required(VERSION 3.15)
project(test_log4cpp CXX)

find_package(log4cpp REQUIRED CONFIG)

add_executable(test_log4cpp test_log4cpp.cpp)
target_compile_features(test_log4cpp PRIVATE cxx_std_11)
target_link_libraries(test_log4cpp PRIVATE log4cpp::log4cpp)
