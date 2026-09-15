cmake_minimum_required(VERSION 3.15)
project(curlcpp_consumer LANGUAGES CXX)

find_package(curlcpp CONFIG REQUIRED)

add_executable(test_curlcpp test.cpp)
target_link_libraries(test_curlcpp PRIVATE curlcpp::curlcpp)
target_compile_features(test_curlcpp PRIVATE cxx_std_11)
