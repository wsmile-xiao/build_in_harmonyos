cmake_minimum_required(VERSION 3.15)
project(test_mythes CXX)

find_package(mythes CONFIG REQUIRED)
add_executable(test_mythes test.cxx)
target_link_libraries(test_mythes PRIVATE mythes::mythes)
