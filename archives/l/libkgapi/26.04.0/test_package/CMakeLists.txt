cmake_minimum_required(VERSION 3.16)
project(test_libkgapi CXX)

find_package(Qt6 REQUIRED COMPONENTS Core Network)
find_package(KPim6GAPI REQUIRED CONFIG)

add_executable(test_libkgapi test_libkgapi.cpp)
target_link_libraries(test_libkgapi PRIVATE Qt6::Core Qt6::Network KPim6::GAPICore KPim6::GAPICalendar)

enable_testing()
add_test(NAME test_libkgapi COMMAND test_libkgapi)
