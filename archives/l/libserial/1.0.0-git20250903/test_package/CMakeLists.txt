cmake_minimum_required(VERSION 3.15)
project(test_package CXX)

find_package(LibSerial CONFIG REQUIRED)

add_executable(test_libserial test_libserial.cpp)
target_link_libraries(test_libserial PRIVATE LibSerial::LibSerial)
target_compile_features(test_libserial PRIVATE cxx_std_17)
