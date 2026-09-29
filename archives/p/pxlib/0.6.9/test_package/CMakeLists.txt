cmake_minimum_required(VERSION 3.12)
project(test_pxlib C)

find_package(pxlib REQUIRED)

add_executable(test_pxlib test_pxlib.c)
target_link_libraries(test_pxlib PRIVATE pxlib::pxlib)

# HarmonyOS PC (OHOS) native test: CMakeToolchain maps the OHOS conan
# profile (os=OHOS) to CMAKE_SYSTEM_NAME=HarmonyOS; on that platform
# compile in the OHOS_TARGET marker and run the extra checks.
add_executable(test_ohos test_ohos.c)
target_link_libraries(test_ohos PRIVATE pxlib::pxlib)
if(CMAKE_SYSTEM_NAME STREQUAL "HarmonyOS")
    target_compile_definitions(test_ohos PRIVATE OHOS_TARGET=1)
endif()
