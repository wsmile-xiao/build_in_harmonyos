cmake_minimum_required(VERSION 3.15)
project(test_onetbb LANGUAGES CXX)

find_package(TBB CONFIG REQUIRED)

add_executable(test_onetbb test_onetbb.cpp)
target_link_libraries(test_onetbb PRIVATE TBB::tbb)
