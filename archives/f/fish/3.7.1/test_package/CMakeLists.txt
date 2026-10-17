cmake_minimum_required(VERSION 3.15)
project(test_fish CXX)

# The actual test is in conanfile.py test() method which runs fish --version
# This CMakeLists.txt exists to satisfy the CMake build step in test_package
message(STATUS "test_fish: CMake build step completed")
