cmake_minimum_required(VERSION 3.15)
project(test_aces_container LANGUAGES CXX)

find_package(aces_container REQUIRED)

add_executable(test_aces_container test_package.cpp)
target_link_libraries(test_aces_container PRIVATE aces_container::aces_container)
