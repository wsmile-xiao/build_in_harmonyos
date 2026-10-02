cmake_minimum_required(VERSION 3.16)
project(test_kjobwidgets CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(KF6JobWidgets REQUIRED)
find_package(Qt6 REQUIRED COMPONENTS Widgets)

add_executable(test_kjobwidgets test.cpp)
target_link_libraries(test_kjobwidgets KF6::JobWidgets Qt6::Widgets)

enable_testing()
add_test(NAME kjobwidgets_smoke COMMAND test_kjobwidgets)
