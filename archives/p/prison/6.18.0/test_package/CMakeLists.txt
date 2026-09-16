cmake_minimum_required(VERSION 3.15)
project(test_prison CXX)

find_package(Qt6 6.11.1 CONFIG REQUIRED COMPONENTS Gui)
find_package(KF6Prison 6.18.0 CONFIG REQUIRED)

add_executable(test_prison test.cpp)
target_link_libraries(test_prison KF6::Prison Qt6::Gui)

if(CMAKE_SYSTEM_NAME STREQUAL "HarmonyOS" OR CMAKE_SYSTEM_NAME STREQUAL "OHOS")
    set_target_properties(test_prison PROPERTIES BUILD_RPATH "$ORIGIN")
    target_link_options(test_prison PRIVATE "-Wl,--disable-new-dtags")
endif()

enable_testing()
add_test(NAME test_prison COMMAND test_prison)
