cmake_minimum_required(VERSION 3.15)
project(test_kstatusnotifieritem CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# KF6StatusNotifierItemConfig.cmake find_dependency() chains resolve through
# CMAKE_PREFIX_PATH (set up in conanfile.py generate() from the direct
# requirements: qtbase, kwindowsystem).
find_package(Qt6 REQUIRED COMPONENTS Core Gui Widgets DBus)
find_package(KF6StatusNotifierItem REQUIRED)

add_executable(test_kstatusnotifieritem test.cpp)
target_link_libraries(test_kstatusnotifieritem
    Qt6::Core Qt6::Gui Qt6::Widgets Qt6::DBus KF6::StatusNotifierItem)

enable_testing()
add_test(NAME test_kstatusnotifieritem COMMAND test_kstatusnotifieritem)
