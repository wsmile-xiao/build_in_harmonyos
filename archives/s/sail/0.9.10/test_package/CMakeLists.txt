cmake_minimum_required(VERSION 3.15)
project(test_sail LANGUAGES CXX)

find_package(Sail CONFIG REQUIRED)

add_executable(test_sail test_sail.cpp)
# SAIL::Sail transitively pulls in sail-common, sail-codecs, sail-manip and
# the codec dependencies (static combined codec library).
target_link_libraries(test_sail PRIVATE SAIL::Sail)
