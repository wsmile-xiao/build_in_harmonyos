cmake_minimum_required(VERSION 3.15)
project(test_ktextwidgets CXX)

# KF6TextWidgetsTargets.cmake references Qt6::Core/Qt6::Widgets targets
find_package(Qt6 REQUIRED COMPONENTS Core Widgets)
find_package(KF6TextWidgets REQUIRED)

add_executable(test_ktextwidgets test.cpp)
target_link_libraries(test_ktextwidgets KF6::TextWidgets)

enable_testing()
add_test(NAME test_ktextwidgets COMMAND test_ktextwidgets)
