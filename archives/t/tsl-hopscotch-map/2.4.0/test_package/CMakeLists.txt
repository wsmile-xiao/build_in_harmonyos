cmake_minimum_required(VERSION 3.13)
project(tsl_hopscotch_map_test LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Package name tsl-hopscotch-map, target tsl::hopscotch_map
find_package(tsl-hopscotch-map REQUIRED)

add_executable(tsl_hopscotch_map_test main.cpp)
target_link_libraries(tsl_hopscotch_map_test PRIVATE tsl::hopscotch_map)

include(CTest)
if(BUILD_TESTING)
    add_test(NAME tsl_hopscotch_map_test COMMAND tsl_hopscotch_map_test)
endif()
