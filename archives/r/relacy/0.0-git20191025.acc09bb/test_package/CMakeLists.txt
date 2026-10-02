cmake_minimum_required(VERSION 3.15)
project(test_relacy LANGUAGES CXX)

find_package(relacy CONFIG REQUIRED)

add_executable(test_relacy test.cpp)
target_compile_features(test_relacy PRIVATE cxx_std_11)
target_link_libraries(test_relacy PRIVATE relacy::relacy)
