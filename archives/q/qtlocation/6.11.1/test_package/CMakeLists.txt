cmake_minimum_required(VERSION 3.16)
project(test_qtlocation LANGUAGES CXX)

find_package(Qt6 6.11.1 REQUIRED COMPONENTS Location)

add_executable(test_qtlocation test_qtlocation.cpp)
target_compile_features(test_qtlocation PRIVATE cxx_std_17)
target_link_libraries(
    test_qtlocation
    PRIVATE Qt6::Location Qt6::Core
)
