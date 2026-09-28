cmake_minimum_required(VERSION 3.15)
project(installation_birthday_test LANGUAGES CXX)

add_executable(installation_birthday_probe installation_birthday_probe.cpp)
set_target_properties(installation_birthday_probe PROPERTIES
    CXX_STANDARD 11
    CXX_STANDARD_REQUIRED ON)
