cmake_minimum_required(VERSION 3.15)
project(test_knotifications5 CXX)

set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)

# Widgets is required by the consumer test: KPassivePopup show/hide cycle
# and QApplication (offscreen platform).
find_package(Qt5 CONFIG REQUIRED Core Widgets)
find_package(KF5Notifications CONFIG REQUIRED)

add_executable(test_knotifications5 test.cpp)
target_link_libraries(test_knotifications5 KF5::Notifications Qt5::Core Qt5::Widgets)

enable_testing()
add_test(NAME test_knotifications5 COMMAND test_knotifications5)
