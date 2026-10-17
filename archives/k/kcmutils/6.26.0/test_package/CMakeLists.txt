cmake_minimum_required(VERSION 3.16)
project(test_kcmutils LANGUAGES CXX)

find_package(Qt6 REQUIRED COMPONENTS Widgets)
find_package(KF6KCMUtils REQUIRED CONFIG)

add_executable(test_kcmutils test_kcmutils.cpp)
target_link_libraries(test_kcmutils PRIVATE Qt6::Widgets KF6::KCMUtilsCore)

enable_testing()
add_test(NAME test_kcmutils COMMAND test_kcmutils)
