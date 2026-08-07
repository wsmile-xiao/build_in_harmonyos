cmake_minimum_required(VERSION 3.15)
project(test_qwt CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# qtbase 提供 Qt6Config.cmake（Qt6::Core/Gui/Widgets）
find_package(Qt6 REQUIRED COMPONENTS Core Gui Widgets)

add_executable(test_qwt test_qwt.cpp)
target_include_directories(test_qwt PRIVATE ${QWT_INCLUDE_DIR})
target_link_directories(test_qwt PRIVATE ${QWT_LIBRARY_DIR})
target_link_libraries(test_qwt Qt6::Core Qt6::Gui Qt6::Widgets qwt)

enable_testing()
add_test(NAME test_qwt COMMAND test_qwt)
