cmake_minimum_required(VERSION 3.15)
project(test_ksvg CXX)

# The upstream KF6SvgConfig.cmake only find_dependency()s Qt6Gui; the
# exported KF6::Svg target's INTERFACE links KF6::ConfigCore, so the
# consumer must make KF6Config discoverable before find_package(KF6Svg)
# resolves the imported interface.
find_package(KF6Config COMPONENTS ConfigCore CONFIG)

find_package(KF6Svg REQUIRED)

add_executable(test_ksvg test.cpp)
target_link_libraries(test_ksvg KF6::Svg)

set_target_properties(test_ksvg PROPERTIES
    CXX_STANDARD 17
    CXX_STANDARD_REQUIRED ON)

enable_testing()
add_test(NAME test_ksvg COMMAND test_ksvg)
