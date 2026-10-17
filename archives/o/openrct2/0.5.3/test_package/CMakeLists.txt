cmake_minimum_required(VERSION 3.15)
project(test_openrct2 CXX)

# openrct2 is an application package; test is binary execution only.
# This file exists for CI structure checks (L0a-L0e).
add_executable(test_placeholder test_main.cpp)
