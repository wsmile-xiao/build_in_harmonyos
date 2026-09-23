cmake_minimum_required(VERSION 3.15)
project(pnm_test LANGUAGES CXX)

find_package(pnm REQUIRED CONFIG)

add_executable(pnm_test test.cpp)
target_compile_features(pnm_test PRIVATE cxx_std_11)
target_link_libraries(pnm_test PRIVATE pnm::pnm)
