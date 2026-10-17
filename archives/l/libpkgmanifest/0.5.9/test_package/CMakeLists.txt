cmake_minimum_required(VERSION 3.13)
project(test_package CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(PkgConfig REQUIRED)
pkg_check_modules(LIBPKGMANIFEST REQUIRED libpkgmanifest)

link_directories(${LIBPKGMANIFEST_LIBRARY_DIRS})
add_executable(test_package src/test_package.cpp)
target_include_directories(test_package PRIVATE ${LIBPKGMANIFEST_INCLUDE_DIRS})
target_link_libraries(test_package PRIVATE ${LIBPKGMANIFEST_LIBRARIES})
