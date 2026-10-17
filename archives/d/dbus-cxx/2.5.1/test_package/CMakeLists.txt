cmake_minimum_required(VERSION 3.12)
project(test_dbuscxx CXX)

find_package(dbus-cxx REQUIRED)

add_executable(test_dbuscxx test_dbuscxx.cpp)
target_link_libraries(test_dbuscxx PRIVATE dbus-cxx::dbus-cxx)
set_property(TARGET test_dbuscxx PROPERTY CXX_STANDARD 17)
