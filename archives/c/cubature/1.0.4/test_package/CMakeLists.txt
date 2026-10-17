cmake_minimum_required(VERSION 3.15)
project(cubature_test_package LANGUAGES C)

find_package(cubature CONFIG REQUIRED)

add_executable(test_cubature test_cubature.c)
target_link_libraries(test_cubature PRIVATE cubature::cubature)

option(CUBATURE_TEST_OHOS "Build the HarmonyOS-specific consumer test" OFF)
if(CUBATURE_TEST_OHOS)
    add_executable(test_cubature_ohos test_cubature_ohos.c)
    target_link_libraries(
        test_cubature_ohos
        PRIVATE cubature::cubature ${CMAKE_DL_LIBS}
    )
endif()
