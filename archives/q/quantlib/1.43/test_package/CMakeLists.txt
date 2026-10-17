cmake_minimum_required(VERSION 3.15)
project(test_quantlib CXX)

find_package(QuantLib CONFIG REQUIRED)

add_executable(test_quantlib test_quantlib.cpp)
target_link_libraries(test_quantlib PRIVATE QuantLib::QuantLib)
