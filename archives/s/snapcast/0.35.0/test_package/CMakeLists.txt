cmake_minimum_required(VERSION 3.15)
project(test_package CXX)

add_executable(${PROJECT_NAME} test_package.cpp)

find_package(snapcast REQUIRED CONFIG)

# The actual test runs snapserver/snapclient --version from conanfile.py test()
