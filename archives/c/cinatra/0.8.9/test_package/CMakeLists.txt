cmake_minimum_required(VERSION 3.15)
project(test_package CXX)

include(CTest)

find_package(cinatra REQUIRED)

add_executable(test_package test_package.cpp)
target_link_libraries(test_package PRIVATE cinatra::cinatra)
target_compile_features(test_package PRIVATE cxx_std_20)
# coroutine support: clang 15 needs -std=c++20 (already) and no extra flags
if(CMAKE_CXX_COMPILER_ID STREQUAL "GNU")
    target_compile_options(test_package PRIVATE -fcoroutines)
endif()

if(BUILD_TESTING)
  add_test(NAME test_package COMMAND test_package)
endif()
