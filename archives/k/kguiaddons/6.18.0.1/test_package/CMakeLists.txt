cmake_minimum_required(VERSION 3.15)
project(test_kguiaddons CXX)

find_package(KF6GuiAddons REQUIRED)

add_executable(test_kguiaddons test.cpp)
target_link_libraries(test_kguiaddons KF6::GuiAddons)

enable_testing()
add_test(NAME test_kguiaddons COMMAND test_kguiaddons)
