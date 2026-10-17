cmake_minimum_required(VERSION 3.15)
project(test_jane_street_headers LANGUAGES CXX)

find_package(jane-street-headers CONFIG REQUIRED)

add_executable(test_jane_street_headers test_jane_street_headers.cpp)
target_compile_features(test_jane_street_headers PRIVATE cxx_std_17)
target_link_libraries(test_jane_street_headers PRIVATE jane-street-headers::jane-street-headers)
