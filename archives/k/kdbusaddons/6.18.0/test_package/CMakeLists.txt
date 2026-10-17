cmake_minimum_required(VERSION 3.21)
project(test_kdbusaddons LANGUAGES CXX)

enable_testing()

find_package(Qt6 REQUIRED COMPONENTS Core DBus)
find_package(KF6DBusAddons REQUIRED)

add_executable(test_kdbusaddons test.cpp)
target_compile_features(test_kdbusaddons PRIVATE cxx_std_17)
target_link_libraries(test_kdbusaddons PRIVATE Qt6::Core Qt6::DBus KF6::DBusAddons)

add_test(NAME test_kdbusaddons COMMAND test_kdbusaddons)
