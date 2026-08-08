cmake_minimum_required(VERSION 3.16)
project(osi_smoke CXX)

find_package(coin-osi REQUIRED CONFIG)

add_executable(osi_smoke osi_smoke.cpp)
target_link_libraries(osi_smoke PRIVATE coin-osi::libosi)

set_target_properties(osi_smoke PROPERTIES
    CXX_STANDARD 17
    CXX_STANDARD_REQUIRED ON
    LINK_SEARCH_START_STATIC ON
)
