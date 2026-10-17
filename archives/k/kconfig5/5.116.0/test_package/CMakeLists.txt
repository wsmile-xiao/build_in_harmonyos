cmake_minimum_required(VERSION 3.15)
project(test_kconfig5 CXX)

find_package(Qt5 CONFIG REQUIRED Core)
find_package(KF5Config CONFIG REQUIRED)

add_executable(test_kconfig5 test.cpp)
target_link_libraries(test_kconfig5 KF5::ConfigCore KF5::ConfigGui Qt5::Core)

enable_testing()
add_test(NAME test_kconfig5 COMMAND test_kconfig5)
