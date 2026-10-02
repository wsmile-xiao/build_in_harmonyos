cmake_minimum_required(VERSION 3.15)
project(test_libcamera LANGUAGES CXX)

find_package(libcamera CONFIG REQUIRED)

add_executable(test_libcamera test.cpp)
target_compile_features(test_libcamera PRIVATE cxx_std_20)
target_link_libraries(test_libcamera PRIVATE libcamera::libcamera)
