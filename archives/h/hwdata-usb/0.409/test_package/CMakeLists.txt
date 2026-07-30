cmake_minimum_required(VERSION 3.15)
project(test_hwdata_usb LANGUAGES CXX)

add_executable(test_hwdata_usb test_hwdata_usb.cpp)
target_compile_features(test_hwdata_usb PRIVATE cxx_std_11)
