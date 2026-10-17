cmake_minimum_required(VERSION 3.16)
project(test_rapidjson LANGUAGES CXX)

find_package(rapidjson 1.1.0.1 CONFIG REQUIRED)

enable_testing()

function(add_rapidjson_consumer target source)
    add_executable(${target} ${source})
    target_compile_features(${target} PRIVATE cxx_std_11)
    target_link_libraries(${target} PRIVATE rapidjson::rapidjson)
    add_test(NAME ${target} COMMAND ${target})
endfunction()

add_rapidjson_consumer(rapidjson_unit_consumer unit.cpp)
add_rapidjson_consumer(rapidjson_ohos_portability ohos_portability.cpp)

if(CMAKE_SYSTEM_NAME STREQUAL "HarmonyOS")
    target_compile_definitions(
        rapidjson_ohos_portability PRIVATE RAPIDJSON_TEST_EXPECT_OHOS=1
    )
endif()
