cmake_minimum_required(VERSION 3.15)
project(test_package LANGUAGES CXX)

find_package(adlplug CONFIG REQUIRED)

add_executable(adlplug_smoke main.cpp)
target_link_libraries(adlplug_smoke PRIVATE adlplug::adlplug)

enable_testing()
add_test(NAME adlplug_smoke COMMAND adlplug_smoke)
