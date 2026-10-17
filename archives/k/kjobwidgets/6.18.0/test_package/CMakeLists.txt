cmake_minimum_required(VERSION 3.15)
project(test_kjobwidgets CXX)

find_package(Qt6 REQUIRED COMPONENTS Core Gui Widgets)
find_package(KF6JobWidgets REQUIRED)

add_executable(test_kjobwidgets test.cpp)
target_link_libraries(test_kjobwidgets KF6::JobWidgets)

enable_testing()
add_test(NAME test_kjobwidgets COMMAND test_kjobwidgets)
