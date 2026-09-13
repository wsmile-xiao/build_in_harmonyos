cmake_minimum_required(VERSION 3.15)
project(test_package LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_AUTOMOC ON)

# KCddb6Targets.cmake transitively references Qt6::Network and KF6Config
# references Qt6::Gui, so load Qt6 first.
find_package(Qt6 REQUIRED COMPONENTS Core Network Gui)
find_package(KF6Config REQUIRED)

find_package(KCddb6 CONFIG REQUIRED)

add_executable(test_package test_package.cpp)
target_link_libraries(test_package PRIVATE KCddb6 Qt6::Network)
