cmake_minimum_required(VERSION 3.15)
project(test_solid CXX)

find_package(Qt6 REQUIRED COMPONENTS Core Xml Gui)
find_package(KF6Solid REQUIRED)

add_executable(test_solid test.cpp)
target_link_libraries(test_solid PRIVATE Qt6::Core KF6::Solid)

enable_testing()
add_test(NAME test_solid COMMAND $<TARGET_FILE:test_solid>)
