cmake_minimum_required(VERSION 3.15)
project(snitch_test_package LANGUAGES CXX)

find_package(snitch CONFIG REQUIRED)

add_executable(test_snitch test_snitch.cpp)
# 目标名随配方 header_only 选项变化（CCI 同款：snitch::snitch /
# snitch::snitch-header-only），两者取其一即可
if(TARGET snitch::snitch)
    target_link_libraries(test_snitch PRIVATE snitch::snitch)
else()
    target_link_libraries(test_snitch PRIVATE snitch::snitch-header-only)
endif()
# 上游 target 自身带 INTERFACE cxx_std_20，这里显式声明消费者侧同样要求
target_compile_features(test_snitch PRIVATE cxx_std_20)
