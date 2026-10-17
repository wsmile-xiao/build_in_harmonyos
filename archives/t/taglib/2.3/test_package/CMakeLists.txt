cmake_minimum_required(VERSION 3.15)
project(test_taglib CXX)

find_package(taglib CONFIG REQUIRED)

add_executable(test_taglib test_taglib.cpp)
target_compile_features(test_taglib PRIVATE cxx_std_17)
target_link_libraries(test_taglib PRIVATE taglib::taglib)
