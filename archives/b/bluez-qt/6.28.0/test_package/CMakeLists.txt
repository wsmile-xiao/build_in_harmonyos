cmake_minimum_required(VERSION 3.16)
project(test_bluez_qt CXX)

# KF6BluezQt 为静态库，其导出目标的链接接口包含 Qt6::Core/Qt6::DBus/Qt6::Network
# （src/CMakeLists PRIVATE Qt6::Network 传播到静态库接口），必须先在
# find_package(KF6BluezQt) 前定义这三个 Qt6 目标，否则 Targets.cmake 找不到。
find_package(Qt6 REQUIRED COMPONENTS Core DBus Network)
find_package(KF6BluezQt REQUIRED)

add_executable(test_bluez_qt test.cpp)
target_link_libraries(test_bluez_qt KF6::BluezQt Qt6::Core)

enable_testing()
add_test(NAME test_bluez_qt COMMAND test_bluez_qt)
