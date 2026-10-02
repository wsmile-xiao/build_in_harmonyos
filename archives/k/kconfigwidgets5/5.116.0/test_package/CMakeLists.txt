cmake_minimum_required(VERSION 3.15)
project(test_kconfigwidgets5 CXX)

set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)

# KF5ConfigWidgets config chains through Qt5/KF5 targets; load Qt5 first.
find_package(Qt5 CONFIG REQUIRED Core Gui Widgets)
find_package(KF5ConfigWidgets CONFIG REQUIRED)

add_executable(test_kconfigwidgets5 test.cpp)
target_link_libraries(test_kconfigwidgets5 KF5::ConfigWidgets Qt5::Core Qt5::Gui Qt5::Widgets)

enable_testing()
add_test(NAME test_kconfigwidgets5 COMMAND test_kconfigwidgets5)
