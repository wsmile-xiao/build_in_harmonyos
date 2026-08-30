cmake_minimum_required(VERSION 3.16)
project(test_qtbase LANGUAGES CXX)

find_package(Qt6 6.11.1 REQUIRED COMPONENTS Core Network Gui Widgets Xml)

add_executable(test_qtbase test_qtbase.cpp)
target_compile_features(test_qtbase PRIVATE cxx_std_17)
target_link_libraries(
    test_qtbase
    PRIVATE Qt6::Core Qt6::Network Qt6::Gui Qt6::Widgets Qt6::Xml
)
