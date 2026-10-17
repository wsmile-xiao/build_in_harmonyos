cmake_minimum_required(VERSION 3.16)
project(kopeninghours_test LANGUAGES CXX)

find_package(KOpeningHours REQUIRED)
find_package(Qt6 REQUIRED COMPONENTS Core)

add_executable(test_kopeninghours test_kopeninghours.cpp)
target_link_libraries(test_kopeninghours PRIVATE KOpeningHours Qt6::Core)
target_compile_features(test_kopeninghours PRIVATE cxx_std_17)
