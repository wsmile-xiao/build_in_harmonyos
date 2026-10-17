cmake_minimum_required(VERSION 3.15)
project(test_physunits CXX)

find_package(PhysUnits REQUIRED)

add_executable(test_physunits test_physunits.cpp)
target_link_libraries(test_physunits PRIVATE PhysUnits::PhysUnits)
set_target_properties(test_physunits PROPERTIES
    CXX_STANDARD 11
    CXX_STANDARD_REQUIRED ON)
