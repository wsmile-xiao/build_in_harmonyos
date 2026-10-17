cmake_minimum_required(VERSION 3.15)
project(test_musicxml CXX)

find_package(libmusicxml REQUIRED)

add_executable(test_musicxml test.cpp)
target_link_libraries(test_musicxml PRIVATE libmusicxml::libmusicxml)
target_compile_features(test_musicxml PRIVATE cxx_std_17)
