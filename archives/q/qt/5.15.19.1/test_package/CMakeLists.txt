cmake_minimum_required(VERSION 3.16)
project(test_qt5 LANGUAGES CXX)

find_package(Qt5 5.15.19 REQUIRED COMPONENTS Core Network Gui Widgets Xml)

add_executable(test_qt5 test_qt5.cpp)
target_compile_features(test_qt5 PRIVATE cxx_std_17)
target_link_libraries(
    test_qt5
    PRIVATE
        Qt5::Core Qt5::Network Qt5::Gui Qt5::Widgets Qt5::Xml
)
