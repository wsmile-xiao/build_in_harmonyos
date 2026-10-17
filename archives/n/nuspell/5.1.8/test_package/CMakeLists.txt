cmake_minimum_required(VERSION 3.15)
project(test_nuspell CXX)

find_package(Nuspell REQUIRED)

add_executable(nuspell_test test_nuspell.cpp)
target_compile_features(nuspell_test PRIVATE cxx_std_17)
target_link_libraries(nuspell_test PRIVATE Nuspell::nuspell)
