cmake_minimum_required(VERSION 3.16)
project(test_kguiaddons5 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

find_package(Qt5 5.15.2 REQUIRED COMPONENTS Gui)
find_package(KF5GuiAddons 5.116.0 REQUIRED)

add_executable(test_kguiaddons5 test.cpp)
target_link_libraries(test_kguiaddons5 PRIVATE Qt5::Gui KF5::GuiAddons)

enable_testing()
add_test(NAME test_kguiaddons5 COMMAND test_kguiaddons5)
