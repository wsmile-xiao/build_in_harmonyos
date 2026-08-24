cmake_minimum_required(VERSION 3.15)
project(test_kconfigwidgets CXX)

# KF6ConfigWidgets config chains through Qt6/KF6 targets; load Qt6 first.
find_package(Qt6 REQUIRED COMPONENTS Core Gui Widgets)
find_package(KF6ConfigWidgets REQUIRED)

add_executable(test_kconfigwidgets test.cpp)
target_link_libraries(test_kconfigwidgets KF6::ConfigWidgets)

enable_testing()
add_test(NAME test_kconfigwidgets COMMAND test_kconfigwidgets)
