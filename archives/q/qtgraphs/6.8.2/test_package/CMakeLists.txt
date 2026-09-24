cmake_minimum_required(VERSION 3.16)
project(test_qtgraphs CXX)

find_package(Qt6 6.8.2 REQUIRED COMPONENTS Graphs Core Gui Qml Quick)

add_executable(test_qtgraphs test_qtgraphs.cpp)
target_link_libraries(test_qtgraphs PRIVATE Qt6::Graphs)
target_link_libraries(test_qtgraphs PRIVATE Qt6::Core)
target_link_libraries(test_qtgraphs PRIVATE Qt6::Gui)
target_link_libraries(test_qtgraphs PRIVATE Qt6::Qml)
target_link_libraries(test_qtgraphs PRIVATE Qt6::Quick)

set_property(TARGET test_qtgraphs PROPERTY CXX_STANDARD 17)
set_property(TARGET test_qtgraphs PROPERTY CXX_STANDARD_REQUIRED ON)
