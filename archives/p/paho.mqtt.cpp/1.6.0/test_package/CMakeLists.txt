cmake_minimum_required(VERSION 3.15)
project(test_paho_mqtt_cpp CXX)

find_package(PahoMqttCpp REQUIRED)

add_executable(test_paho_mqtt_cpp test.cpp)
target_link_libraries(test_paho_mqtt_cpp PahoMqttCpp::paho-mqttpp3)

enable_testing()
add_test(NAME test_paho_mqtt_cpp COMMAND test_paho_mqtt_cpp)

if(CMAKE_SYSTEM_NAME MATCHES "^(HarmonyOS|OHOS)$")
    add_executable(test_paho_mqtt_cpp_ohos test_ohos.cpp)
    target_link_libraries(test_paho_mqtt_cpp_ohos PahoMqttCpp::paho-mqttpp3)
    set_target_properties(test_paho_mqtt_cpp_ohos PROPERTIES
        CXX_STANDARD 17
        CXX_STANDARD_REQUIRED ON
        CXX_EXTENSIONS OFF
    )
    add_test(NAME test_paho_mqtt_cpp_ohos COMMAND test_paho_mqtt_cpp_ohos)
endif()
