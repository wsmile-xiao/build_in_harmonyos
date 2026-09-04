cmake_minimum_required(VERSION 3.21)
project(test_libical LANGUAGES C)

enable_testing()

find_package(LibIcal REQUIRED CONFIG)

add_executable(test_libical test_libical.c)
target_link_libraries(test_libical PRIVATE ical icalvcard)

if(CMAKE_SYSTEM_NAME STREQUAL "HarmonyOS" OR CMAKE_SYSTEM_NAME STREQUAL "OHOS")
    set_target_properties(test_libical PROPERTIES BUILD_RPATH "$ORIGIN")
    target_link_options(test_libical PRIVATE "-Wl,-rpath,$ORIGIN" "-Wl,--disable-new-dtags")
endif()

add_test(NAME test_libical COMMAND test_libical)
