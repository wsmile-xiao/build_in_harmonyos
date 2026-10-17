cmake_minimum_required(VERSION 3.15)
project(test_pcg_cpp CXX)

find_package(pcg-cpp CONFIG REQUIRED)

add_executable(test_pcg_cpp test_pcg.cpp)
target_link_libraries(test_pcg_cpp PRIVATE pcg-cpp::pcg-cpp)
set_property(TARGET test_pcg_cpp PROPERTY CXX_STANDARD 11)
