cmake_minimum_required(VERSION 3.16)
project(test_qtimageformats LANGUAGES CXX)

find_package(Qt6 6.11.1 REQUIRED COMPONENTS Gui)

add_executable(test_qtimageformats test_qtimageformats.cpp)
target_compile_features(test_qtimageformats PRIVATE cxx_std_17)
target_link_libraries(test_qtimageformats PRIVATE Qt6::Gui)
