cmake_minimum_required(VERSION 3.16)
project(recastnavigation_test CXX)

find_package(recastnavigation REQUIRED CONFIG)

add_executable(recastnavigation_test test.cpp)
target_link_libraries(recastnavigation_test
    RecastNavigation::Recast
    RecastNavigation::Detour
    RecastNavigation::DetourCrowd
    RecastNavigation::DetourTileCache
    RecastNavigation::DebugUtils
)
