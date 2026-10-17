cmake_minimum_required(VERSION 3.13)
project(ordered_map_test LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 11)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Upstream project name is tsl-ordered-map, target is tsl::ordered_map
find_package(tsl-ordered-map REQUIRED)

add_executable(ordered_map_test main.cpp)
target_link_libraries(ordered_map_test PRIVATE tsl::ordered_map)

if(ORDERED_MAP_OHOS_TEST)
    target_link_options(ordered_map_test PRIVATE -static)
endif()
