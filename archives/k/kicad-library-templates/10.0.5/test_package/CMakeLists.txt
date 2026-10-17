cmake_minimum_required(VERSION 3.15)
project(kicad_library_templates_test LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

add_executable(kicad_templates_probe test_package.cpp)

if(CMAKE_SYSTEM_NAME STREQUAL "OHOS" OR CMAKE_SYSTEM_NAME STREQUAL "HarmonyOS")
    add_executable(kicad_templates_harmonyos_probe harmonyos_specific_test.cpp)
endif()
