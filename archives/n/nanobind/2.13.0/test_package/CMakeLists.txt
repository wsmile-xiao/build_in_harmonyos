cmake_minimum_required(VERSION 3.15)
project(nanobind_test LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# nanobind requires Python >= 3.9; OHOS package aligns with 3.12.x
find_package(Python 3.9 COMPONENTS Interpreter Development.Module REQUIRED)

find_package(nanobind CONFIG REQUIRED)
find_package(tsl-robin-map CONFIG REQUIRED)

nanobind_add_module(my_ext my_ext.cpp)
