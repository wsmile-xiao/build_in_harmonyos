cmake_minimum_required(VERSION 3.16)
project(test_corepdf LANGUAGES CXX)

# Test just needs to build a dummy target; the real test runs the corepdf binary
add_executable(test_corepdf test_corepdf.cpp)
