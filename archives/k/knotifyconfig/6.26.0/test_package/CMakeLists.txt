cmake_minimum_required(VERSION 3.15)
project(test_knotifyconfig CXX)

# The installed KF6NotifyConfigConfig.cmake calls
# find_dependency(Qt6Widgets), and KF6NotifyConfigTargets.cmake references
# Qt6::Widgets targets, so load Qt6 first.
find_package(Qt6 REQUIRED COMPONENTS Widgets)
find_package(KF6NotifyConfig REQUIRED)

add_executable(test_knotifyconfig test_knotifyconfig.cpp)
target_link_libraries(test_knotifyconfig KF6::NotifyConfig)

enable_testing()
add_test(NAME test_knotifyconfig COMMAND test_knotifyconfig)
