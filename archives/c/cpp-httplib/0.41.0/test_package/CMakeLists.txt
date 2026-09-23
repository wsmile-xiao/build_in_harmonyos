cmake_minimum_required(VERSION 3.15)
project(cpp_httplib_test_package LANGUAGES CXX)

find_package(httplib CONFIG REQUIRED)

add_executable(test_package test_package.cpp)
target_link_libraries(test_package PRIVATE httplib::httplib)
target_compile_features(test_package PRIVATE cxx_std_11)

option(CPP_HTTPLIB_BUILD_HARMONYOS_TEST "Build the HarmonyOS-only consumer" OFF)
if(CPP_HTTPLIB_BUILD_HARMONYOS_TEST)
    add_executable(harmonyos_test harmonyos_test.cpp)
    target_link_libraries(harmonyos_test PRIVATE httplib::httplib)
    target_compile_features(harmonyos_test PRIVATE cxx_std_11)
endif()
