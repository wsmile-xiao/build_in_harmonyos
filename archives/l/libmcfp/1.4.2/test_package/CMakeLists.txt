cmake_minimum_required(VERSION 3.15)
project(test_libmcfp LANGUAGES CXX)

find_package(libmcfp REQUIRED)

add_executable(test_libmcfp src/test_libmcfp.cpp)
target_link_libraries(test_libmcfp libmcfp::libmcfp)
set_target_properties(test_libmcfp PROPERTIES CXX_STANDARD 20)
