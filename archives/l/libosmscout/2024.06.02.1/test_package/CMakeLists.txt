cmake_minimum_required(VERSION 3.20)
project(test_libosmscout CXX)

enable_testing()

find_package(libosmscout REQUIRED)

add_executable(test_libosmscout test_libosmscout.cpp)
target_compile_features(test_libosmscout PRIVATE cxx_std_17)
target_compile_definitions(test_libosmscout PRIVATE
    OSMSCOUT_TEST_STYLESHEETS="${OSMSCOUT_TEST_STYLESHEETS}")
target_link_libraries(test_libosmscout PRIVATE
    OSMScout::OSMScout
    OSMScout::Map
    OSMScout::MapSVG
    OSMScout::Import
    OSMScout::GPX
    OSMScout::Client)

add_test(NAME consumer_end_to_end COMMAND test_libosmscout)
