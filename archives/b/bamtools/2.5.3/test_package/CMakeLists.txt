cmake_minimum_required(VERSION 3.15)
project(test_bamtools LANGUAGES CXX)

find_package(bamtools REQUIRED CONFIG)

add_executable(test_bamtools test.cpp)
target_link_libraries(test_bamtools PRIVATE bamtools::bamtools)
target_compile_features(test_bamtools PRIVATE cxx_std_11)

enable_testing()
add_test(NAME test_bamtools COMMAND test_bamtools)
