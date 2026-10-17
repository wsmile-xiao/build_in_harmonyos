cmake_minimum_required(VERSION 3.15)
project(mini_test_package CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# 消费者契约：conan 生成的 mINI-config.cmake -> mINI::mINI
find_package(mINI CONFIG REQUIRED)

add_executable(mini_consumer test_mini_consumer.cpp)
target_link_libraries(mini_consumer PRIVATE mINI::mINI)
