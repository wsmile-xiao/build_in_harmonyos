cmake_minimum_required(VERSION 3.16)
project(test_sparsepp LANGUAGES CXX)

find_package(sparsepp CONFIG REQUIRED)

add_executable(sparsepp_consumer test.cpp)
target_compile_features(sparsepp_consumer PRIVATE cxx_std_11)
target_link_libraries(sparsepp_consumer PRIVATE sparsepp::sparsepp)
