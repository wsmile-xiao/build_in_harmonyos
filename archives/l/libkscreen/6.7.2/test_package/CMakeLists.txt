cmake_minimum_required(VERSION 3.15)
project(test_libkscreen CXX)

# KF6Screen public headers use operator<=> (C++20).
set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(Qt6 REQUIRED COMPONENTS Core Gui DBus)
find_package(KF6Screen REQUIRED)

add_executable(test_libkscreen test.cpp)
target_link_libraries(test_libkscreen KF6::Screen Qt::Core Qt::Gui Qt::DBus)

enable_testing()
add_test(NAME test_libkscreen COMMAND test_libkscreen)
