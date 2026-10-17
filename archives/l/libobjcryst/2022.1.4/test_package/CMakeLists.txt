cmake_minimum_required(VERSION 3.15)
project(test_libobjcryst CXX)

set(CMAKE_CXX_STANDARD 14)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(ObjCryst CONFIG REQUIRED)

add_executable(test_libobjcryst test.cpp)
target_link_libraries(test_libobjcryst PRIVATE ObjCryst::ObjCryst)
