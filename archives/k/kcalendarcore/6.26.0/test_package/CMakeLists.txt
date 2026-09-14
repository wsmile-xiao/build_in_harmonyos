cmake_minimum_required(VERSION 3.16)
project(test_kcalendarcore LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_AUTOMOC OFF)

find_package(Qt6 REQUIRED COMPONENTS Core Gui)
find_package(KF6CalendarCore REQUIRED)

add_executable(test_kcalendarcore test.cpp)
target_link_libraries(
    test_kcalendarcore
    PRIVATE
        Qt6::Core
        Qt6::Gui
        KF6::CalendarCore
)

enable_testing()
add_test(NAME test_kcalendarcore COMMAND test_kcalendarcore)
