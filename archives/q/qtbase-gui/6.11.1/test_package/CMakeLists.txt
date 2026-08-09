cmake_minimum_required(VERSION 3.16)
project(test_qtbase_gui LANGUAGES CXX)

find_package(Qt6 6.11.1 REQUIRED COMPONENTS Core Network Gui Widgets Xml)

add_executable(test_qtbase_gui test_qtbase_gui.cpp)
target_compile_features(test_qtbase_gui PRIVATE cxx_std_17)
target_link_libraries(
    test_qtbase_gui
    PRIVATE Qt6::Core Qt6::Network Qt6::Gui Qt6::Widgets Qt6::Xml
)
