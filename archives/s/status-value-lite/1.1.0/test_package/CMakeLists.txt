cmake_minimum_required(VERSION 3.5 FATAL_ERROR)
project(test_status_value LANGUAGES CXX)

find_package(status-value-lite REQUIRED)

add_executable(test_status_value test_status_value.cpp)
target_link_libraries(test_status_value PRIVATE nonstd::status_value-lite)
target_compile_features(test_status_value PRIVATE cxx_std_17)
