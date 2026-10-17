cmake_minimum_required(VERSION 3.16)
project(test_kdbusaddons CXX)

find_package(KF6DBusAddons REQUIRED)

add_executable(test_kdbusaddons test.cpp)
target_link_libraries(test_kdbusaddons KF6::DBusAddons Qt6::DBus)

enable_testing()
add_test(NAME test_kdbusaddons COMMAND test_kdbusaddons)
