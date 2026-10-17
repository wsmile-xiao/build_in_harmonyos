cmake_minimum_required(VERSION 3.15)
project(test_libgdsii CXX)

find_package(libgdsii REQUIRED CONFIG)

add_executable(test_libgdsii test_libgdsii.cpp)
target_link_libraries(test_libgdsii PRIVATE libgdsii::libgdsii)
target_compile_features(test_libgdsii PRIVATE cxx_std_11)

