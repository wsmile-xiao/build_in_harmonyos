cmake_minimum_required(VERSION 3.15)
project(test_kcontacts CXX)

find_package(Qt6 6.11.1 CONFIG REQUIRED COMPONENTS Gui)
find_package(KF6Contacts 6.14.0 CONFIG REQUIRED)

add_executable(test_kcontacts test.cpp)
target_link_libraries(test_kcontacts KF6::Contacts)

# OHOS-specific consumer check: the executable must reference KF6Contacts
# through the library SONAME (relative DT_NEEDED), the property the
# recipe-layer SONAME override (cmake_system_name=OHOS +
# CMAKE_USER_MAKE_RULES_OVERRIDE) exists to guarantee.
add_executable(test_kcontacts_ohos test_ohos_soname.cpp)
target_link_libraries(test_kcontacts_ohos KF6::Contacts)

if(CMAKE_SYSTEM_NAME STREQUAL "HarmonyOS" OR CMAKE_SYSTEM_NAME STREQUAL "OHOS")
    set_target_properties(test_kcontacts PROPERTIES BUILD_RPATH "$ORIGIN")
    target_link_options(test_kcontacts PRIVATE "-Wl,--disable-new-dtags")
    set_target_properties(test_kcontacts_ohos PROPERTIES BUILD_RPATH "$ORIGIN")
    target_link_options(test_kcontacts_ohos PRIVATE "-Wl,--disable-new-dtags")
    target_compile_definitions(test_kcontacts_ohos PRIVATE TP_REQUIRE_OHOS)
endif()

enable_testing()
add_test(NAME test_kcontacts COMMAND test_kcontacts)
add_test(NAME test_kcontacts_ohos COMMAND test_kcontacts_ohos)
