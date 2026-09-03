cmake_minimum_required(VERSION 3.15)
project(test_kcontacts CXX)

find_package(Qt6 6.11.1 CONFIG REQUIRED COMPONENTS Gui)
find_package(KF6Contacts 6.18.0 CONFIG REQUIRED)

add_executable(test_kcontacts test.cpp)
target_link_libraries(test_kcontacts KF6::Contacts)

if(CMAKE_SYSTEM_NAME STREQUAL "HarmonyOS" OR CMAKE_SYSTEM_NAME STREQUAL "OHOS")
    set_target_properties(test_kcontacts PROPERTIES BUILD_RPATH "$ORIGIN")
    target_link_options(test_kcontacts PRIVATE "-Wl,--disable-new-dtags")
endif()

enable_testing()
add_test(NAME test_kcontacts COMMAND test_kcontacts)
