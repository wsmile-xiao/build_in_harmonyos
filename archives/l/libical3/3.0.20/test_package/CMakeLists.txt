cmake_minimum_required(VERSION 3.15)
project(test_libical3 LANGUAGES C)

enable_testing()

find_package(PkgConfig REQUIRED)
pkg_check_modules(GLIB2 REQUIRED IMPORTED_TARGET glib-2.0 gobject-2.0)

find_package(LibIcal REQUIRED CONFIG)

add_executable(test_libical3 test_libical3.c)
target_compile_definitions(test_libical3 PRIVATE LIBICAL_GLIB_UNSTABLE_API=1)
target_link_libraries(test_libical3 PRIVATE ical icalss icalvcal ical-glib PkgConfig::GLIB2)

if(CMAKE_SYSTEM_NAME STREQUAL "HarmonyOS" OR CMAKE_SYSTEM_NAME STREQUAL "OHOS")
    set_target_properties(test_libical3 PROPERTIES BUILD_RPATH "$ORIGIN")
    target_link_options(test_libical3 PRIVATE "-Wl,-rpath,$ORIGIN" "-Wl,--disable-new-dtags")
endif()

add_test(NAME test_libical3 COMMAND test_libical3)
