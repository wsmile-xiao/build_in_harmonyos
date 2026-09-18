cmake_minimum_required(VERSION 3.15)
project(test_kglobalaccel CXX)

find_package(KF6GlobalAccel REQUIRED)
find_package(Qt6 REQUIRED COMPONENTS Widgets)

add_executable(test_kglobalaccel test.cpp)
target_link_libraries(test_kglobalaccel KF6::GlobalAccel Qt6::Widgets)

enable_testing()
add_test(NAME test_kglobalaccel COMMAND test_kglobalaccel)
