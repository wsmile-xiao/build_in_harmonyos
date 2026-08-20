cmake_minimum_required(VERSION 3.15)
project(test_entt CXX)

find_package(EnTT CONFIG REQUIRED)

add_executable(test_entt test_entt.cpp)
target_link_libraries(test_entt PRIVATE EnTT::EnTT)
target_compile_features(test_entt PRIVATE cxx_std_20)

if(CMAKE_SYSTEM_NAME STREQUAL "Linux" OR CMAKE_SYSTEM_NAME STREQUAL "OHOS")
    target_compile_options(test_entt PRIVATE -Wno-error)
endif()
