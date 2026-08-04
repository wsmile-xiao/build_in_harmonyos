cmake_minimum_required(VERSION 3.15)
project(test_dyld_headers LANGUAGES CXX)

find_package(dyld-headers CONFIG REQUIRED)

add_executable(test_dyld_headers test_dyld_headers.cpp)
target_compile_features(test_dyld_headers PRIVATE cxx_std_17)
target_link_libraries(test_dyld_headers PRIVATE dyld-headers::dyld-headers)
