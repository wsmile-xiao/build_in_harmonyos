cmake_minimum_required(VERSION 3.17)
project(test_adwaita_qt LANGUAGES CXX)

find_package(Qt6 6.11.1 REQUIRED COMPONENTS Core Gui Widgets)
find_package(AdwaitaQt6 CONFIG REQUIRED)

if(NOT TARGET adwaitaqt6)
    message(FATAL_ERROR "AdwaitaQt6 package did not export target adwaitaqt6")
endif()

add_executable(test_adwaita_qt test_adwaita_qt.cpp)
target_compile_features(test_adwaita_qt PRIVATE cxx_std_17)
target_include_directories(test_adwaita_qt PRIVATE "${ADWAITAQT_INCLUDE_DIRS}")
target_link_libraries(
    test_adwaita_qt
    PRIVATE
        Qt6::Core
        Qt6::Gui
        Qt6::Widgets
        adwaitaqt6
)
