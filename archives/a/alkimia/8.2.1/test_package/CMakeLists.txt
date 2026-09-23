cmake_minimum_required(VERSION 3.16)
project(test_package CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(Qt6 REQUIRED COMPONENTS Core)
# alkimia installs LibAlkimia6Config.cmake under lib/cmake; it is located
# through CMAKE_PREFIX_PATH (cmake_find_mode=none).
find_package(LibAlkimia6 8.2.1 REQUIRED)

add_executable(test_package test_package.cpp)
target_link_libraries(test_package PRIVATE Alkimia::alkimia Qt6::Core)
