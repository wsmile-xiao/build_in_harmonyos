cmake_minimum_required(VERSION 3.15)

project(physunits_consumer CXX)

find_package(PhysUnits-CT CONFIG REQUIRED)

add_executable(physunits_consumer test_package.cpp)
target_link_libraries(physunits_consumer PRIVATE PhysUnits::PhysUnits)
