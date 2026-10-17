cmake_minimum_required(VERSION 3.15)
project(physunits_consumer LANGUAGES CXX)

find_package(PhysUnits CONFIG REQUIRED)

add_executable(physunits_consumer test_package.cpp)
target_compile_features(physunits_consumer PRIVATE cxx_std_11)
target_link_libraries(physunits_consumer PRIVATE PhysUnits::PhysUnits)

enable_testing()
add_test(NAME physunits_consumer COMMAND physunits_consumer)
