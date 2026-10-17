cmake_minimum_required(VERSION 3.15)
project(test_package CXX)

find_package(clucene CONFIG REQUIRED)

add_executable(test_clucene test_clucene.cpp)
target_link_libraries(test_clucene PRIVATE clucene::clucene)
target_compile_features(test_clucene PRIVATE cxx_std_11)

add_executable(test_analyzer test_analyzer.cpp)
target_link_libraries(test_analyzer PRIVATE clucene::clucene)
target_compile_features(test_analyzer PRIVATE cxx_std_11)
