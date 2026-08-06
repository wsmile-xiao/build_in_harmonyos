cmake_minimum_required(VERSION 3.16)
project(test_lightgbm CXX)

find_package(lightgbm REQUIRED CONFIG)

add_executable(test_lightgbm_api test_lightgbm_api.cpp)
target_link_libraries(test_lightgbm_api PRIVATE lightgbm::lightgbm)
