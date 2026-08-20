cmake_minimum_required(VERSION 3.15)
project(test_thorvg CXX)

find_package(thorvg REQUIRED CONFIG)
add_executable(test_thorvg test_thorvg.cpp)
target_compile_features(test_thorvg PRIVATE cxx_std_14)
target_link_libraries(test_thorvg PRIVATE thorvg::thorvg)
