cmake_minimum_required(VERSION 3.16)
project(minidjvu_test_package LANGUAGES CXX)

find_package(minidjvu CONFIG REQUIRED)

add_executable(test_minidjvu test.cpp)
target_compile_features(test_minidjvu PRIVATE cxx_std_17)
target_link_libraries(test_minidjvu PRIVATE minidjvu::minidjvu)

add_executable(test_minidjvu_ohos test_ohos.cpp)
target_compile_features(test_minidjvu_ohos PRIVATE cxx_std_17)
target_link_libraries(test_minidjvu_ohos PRIVATE minidjvu::minidjvu)
