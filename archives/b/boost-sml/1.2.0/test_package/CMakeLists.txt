cmake_minimum_required(VERSION 3.16)
project(boost_sml_test_package CXX)

find_package(boost-sml REQUIRED CONFIG)
# 注意：header-only 包可能不生成 CMake config，走 include 目录兜底
if(NOT TARGET boost-sml::boost-sml)
    add_executable(test_package test.cpp)
    target_include_directories(test_package PRIVATE ${boost-sml_INCLUDE_DIRS})
else()
    add_executable(test_package test.cpp)
    target_link_libraries(test_package PRIVATE boost-sml::boost-sml)
endif()

enable_testing()
add_test(NAME boost_sml_smoke COMMAND test_package)
