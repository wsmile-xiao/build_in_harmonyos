cmake_minimum_required(VERSION 3.15)
project(test_wolfmqtt C)

# Find the package via Conan-generated CMakeDeps
find_package(wolfmqtt REQUIRED)
find_package(wolfssl REQUIRED)

# Consumer test: exercises the public MqttClient_Init/DeInit lifecycle
# (installed headers + linked library only).
add_executable(test_wolfmqtt test.c)
target_link_libraries(test_wolfmqtt wolfmqtt::wolfmqtt wolfssl::wolfssl)

# HarmonyOS-specific test: MqttEncode_Connect wire-byte assertions plus
# feature-macro ABI propagation checks; runs on the OHOS target.
add_executable(test_ohos test_ohos.c)
target_link_libraries(test_ohos wolfmqtt::wolfmqtt wolfssl::wolfssl)

# wolfmqtt public headers include <wolfssl/options.h> (ENABLE_MQTT_TLS build).
# The published wolfssl package ships empty cpp_info.include_dirs, so add its
# include dir explicitly from the CMakeDeps package-folder variable.
target_include_directories(test_wolfmqtt PRIVATE
    ${wolfmqtt_PACKAGE_FOLDER_RELEASE}/include
    ${wolfssl_PACKAGE_FOLDER_RELEASE}/include)
target_include_directories(test_ohos PRIVATE
    ${wolfmqtt_PACKAGE_FOLDER_RELEASE}/include
    ${wolfssl_PACKAGE_FOLDER_RELEASE}/include)
target_compile_definitions(test_wolfmqtt PRIVATE ENABLE_MQTT_TLS WOLFMQTT_SN
    WOLFMQTT_V5 WOLFMQTT_NONBLOCK WOLFMQTT_MULTITHREAD WOLFMQTT_BROKER)
target_compile_definitions(test_ohos PRIVATE ENABLE_MQTT_TLS WOLFMQTT_SN
    WOLFMQTT_V5 WOLFMQTT_NONBLOCK WOLFMQTT_MULTITHREAD WOLFMQTT_BROKER)

enable_testing()
add_test(NAME test_wolfmqtt COMMAND test_wolfmqtt)
add_test(NAME test_ohos COMMAND test_ohos)
