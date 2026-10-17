cmake_minimum_required(VERSION 3.15)
project(test_wave CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(Boost REQUIRED COMPONENTS wave filesystem)

add_executable(test_wave test_wave.cpp)
target_link_libraries(test_wave PRIVATE Boost::wave Boost::filesystem)
