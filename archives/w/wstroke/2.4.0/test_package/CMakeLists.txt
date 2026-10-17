cmake_minimum_required(VERSION 3.15)
project(test_package CXX C)

find_package(wstroke CONFIG REQUIRED)

add_executable(test_wstroke test_wstroke.cpp)
target_link_libraries(test_wstroke PRIVATE wstroke::wstroke)
# stroke core needs math
if(UNIX)
    target_link_libraries(test_wstroke PRIVATE m)
endif()
target_compile_features(test_wstroke PRIVATE cxx_std_17)
