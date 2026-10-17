cmake_minimum_required(VERSION 3.15)
project(astyle_consumer LANGUAGES CXX)

find_package(astyle CONFIG REQUIRED)

add_executable(astyle_consumer test.cpp)
target_compile_features(astyle_consumer PRIVATE cxx_std_17)
target_link_libraries(astyle_consumer PRIVATE astyle::astyle)
