cmake_minimum_required(VERSION 3.15)
project(test_knewstuff CXX)

find_package(Qt6 REQUIRED COMPONENTS Core Widgets Gui)
find_package(KF6NewStuff REQUIRED COMPONENTS Core Widgets)

add_executable(test_knewstuff test.cpp)
target_link_libraries(test_knewstuff PRIVATE KF6::NewStuffCore KF6::NewStuffWidgets Qt6::Widgets)

enable_testing()
add_test(NAME test_knewstuff COMMAND test_knewstuff)
