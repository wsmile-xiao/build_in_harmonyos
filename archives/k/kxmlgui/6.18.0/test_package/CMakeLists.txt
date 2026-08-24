cmake_minimum_required(VERSION 3.15)
project(test_kxmlgui CXX)

# KF6XmlGui config chains through Qt6/KF6 targets; load Qt6 first.
find_package(Qt6 REQUIRED COMPONENTS Core Gui Widgets)
find_package(KF6XmlGui REQUIRED)

add_executable(test_kxmlgui test.cpp)
target_link_libraries(test_kxmlgui KF6::XmlGui)

enable_testing()
add_test(NAME test_kxmlgui COMMAND test_kxmlgui)
