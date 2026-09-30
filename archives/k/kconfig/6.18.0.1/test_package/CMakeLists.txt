cmake_minimum_required(VERSION 3.15)
project(test_kconfig CXX)

# KF6ConfigTargets.cmake references Qt6::Core/Qt6::Xml targets, so load
# Qt6 first.
find_package(Qt6 REQUIRED COMPONENTS Core Xml)
find_package(KF6Config REQUIRED)

add_executable(test_kconfig test.cpp)
target_link_libraries(test_kconfig KF6::ConfigCore)

enable_testing()
add_test(NAME test_kconfig COMMAND test_kconfig)
