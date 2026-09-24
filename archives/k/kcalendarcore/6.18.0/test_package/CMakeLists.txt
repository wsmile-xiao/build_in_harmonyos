cmake_minimum_required(VERSION 3.21)
project(test_kcalendarcore LANGUAGES CXX)

enable_testing()

find_package(KF6CalendarCore REQUIRED CONFIG)
find_package(Qt6 REQUIRED COMPONENTS Core Gui)

add_executable(test_kcalendarcore test_kcalendarcore.cpp)
target_link_libraries(test_kcalendarcore PRIVATE KF6::CalendarCore Qt6::Core Qt6::Gui)

if(CMAKE_SYSTEM_NAME STREQUAL "HarmonyOS" OR CMAKE_SYSTEM_NAME STREQUAL "OHOS")
    set_target_properties(test_kcalendarcore PROPERTIES BUILD_RPATH "$ORIGIN")
    target_link_options(test_kcalendarcore PRIVATE "-Wl,-rpath,$ORIGIN" "-Wl,--disable-new-dtags")
endif()

add_test(NAME test_kcalendarcore COMMAND test_kcalendarcore)
