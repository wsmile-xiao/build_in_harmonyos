cmake_minimum_required(VERSION 3.15)
project(test_pbc LANGUAGES CXX)

find_package(pbc CONFIG REQUIRED)

add_executable(test_pbc test.cpp)
target_compile_features(test_pbc PRIVATE cxx_std_17)
target_link_libraries(test_pbc PRIVATE pbc::pbc)
