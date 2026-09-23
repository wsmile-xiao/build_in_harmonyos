cmake_minimum_required(VERSION 3.15)
project(test_libgdf CXX)

set(CMAKE_CXX_STANDARD 11)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(GDF CONFIG REQUIRED)

add_executable(test_libgdf test_libgdf.cpp)
if(TARGET GDF::GDF)
    target_link_libraries(test_libgdf PRIVATE GDF::GDF)
else()
    target_link_libraries(test_libgdf PRIVATE GDF)
endif()
