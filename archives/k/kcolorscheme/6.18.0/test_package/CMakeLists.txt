cmake_minimum_required(VERSION 3.15)
project(test_kcolorscheme CXX)

# KF6ConfigTargets.cmake references Qt6::Core/Qt6::Gui targets, so load
# Qt6 first.
find_package(Qt6 REQUIRED COMPONENTS Core Gui Widgets)
find_package(KF6ColorScheme REQUIRED)

add_executable(test_kcolorscheme test.cpp)
target_link_libraries(test_kcolorscheme KF6::ColorScheme)

enable_testing()
add_test(NAME test_kcolorscheme COMMAND test_kcolorscheme)
