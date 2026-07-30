cmake_minimum_required(VERSION 3.15)
project(test_package LANGUAGES CXX)

find_package(CLHEP CONFIG REQUIRED)

add_executable(test_clhep test_clhep.cpp)
target_link_libraries(test_clhep PRIVATE CLHEP::CLHEP)
target_compile_features(test_clhep PRIVATE cxx_std_11)

include(CTest)
add_test(NAME clhep_functional_test COMMAND test_clhep)
