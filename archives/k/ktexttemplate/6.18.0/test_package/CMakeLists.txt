cmake_minimum_required(VERSION 3.15)
project(test_ktexttemplate CXX)

find_package(Qt6 6.11.1 CONFIG REQUIRED COMPONENTS Core)
find_package(KF6TextTemplate 6.18.0 CONFIG REQUIRED)

add_executable(test_ktexttemplate test.cpp)
target_link_libraries(test_ktexttemplate KF6::TextTemplate Qt6::Core)

if(CMAKE_SYSTEM_NAME STREQUAL "HarmonyOS" OR CMAKE_SYSTEM_NAME STREQUAL "OHOS")
    set_target_properties(test_ktexttemplate PROPERTIES BUILD_RPATH "$ORIGIN")
    target_link_options(test_ktexttemplate PRIVATE "-Wl,--disable-new-dtags")
endif()

enable_testing()
add_test(NAME test_ktexttemplate COMMAND test_ktexttemplate)
