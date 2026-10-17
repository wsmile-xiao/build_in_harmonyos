cmake_minimum_required(VERSION 3.15)
project(test_package CXX)

find_package(apitrace REQUIRED)

add_executable(test_package test_package.cpp)
