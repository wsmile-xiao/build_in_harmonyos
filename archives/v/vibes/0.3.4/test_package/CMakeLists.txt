cmake_minimum_required(VERSION 3.15)
project(test_vibes CXX)

find_package(vibes CONFIG REQUIRED)

add_executable(test_vibes test_vibes.cpp)
target_link_libraries(test_vibes PRIVATE vibes::vibes)
set_property(TARGET test_vibes PROPERTY CXX_STANDARD 11)
set_property(TARGET test_vibes PROPERTY CXX_STANDARD_REQUIRED ON)
