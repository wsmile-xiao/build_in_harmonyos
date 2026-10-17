cmake_minimum_required(VERSION 3.16)
project(test_jsoncpp LANGUAGES CXX)

find_package(JsonCpp 1.9.8 CONFIG REQUIRED)

enable_testing()

function(add_jsoncpp_consumer target source)
    add_executable(${target} ${source})
    target_compile_features(${target} PRIVATE cxx_std_11)
    target_link_libraries(${target} PRIVATE JsonCpp::JsonCpp)
    add_test(NAME ${target} COMMAND ${target})
endfunction()

add_jsoncpp_consumer(jsoncpp_unit_consumer unit.cpp)
add_jsoncpp_consumer(jsoncpp_integration_consumer integration.cpp)
add_jsoncpp_consumer(jsoncpp_ohos_portability ohos_portability.cpp)

if(CMAKE_SYSTEM_NAME STREQUAL "HarmonyOS")
    target_compile_definitions(
        jsoncpp_ohos_portability PRIVATE JSONCPP_TEST_EXPECT_OHOS=1
    )
endif()
