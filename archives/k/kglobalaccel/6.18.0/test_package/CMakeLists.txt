cmake_minimum_required(VERSION 3.15)
project(test_kglobalaccel CXX)

find_package(Qt6 REQUIRED COMPONENTS Core Gui Widgets DBus)
find_package(KF6GlobalAccel REQUIRED)

add_executable(test_kglobalaccel test.cpp)
target_link_libraries(test_kglobalaccel KF6::GlobalAccel)

if(CMAKE_CXX_COMPILER_ID MATCHES "Clang|GNU")
    target_link_options(test_kglobalaccel PRIVATE "-Wl,-rpath,$ORIGIN" "-Wl,--disable-new-dtags")
endif()
