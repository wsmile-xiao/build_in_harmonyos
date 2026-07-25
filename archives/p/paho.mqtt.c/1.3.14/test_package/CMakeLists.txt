cmake_minimum_required(VERSION 3.15)
project(test_paho_mqtt_c C)

# Find the package via Conan-generated CMakeDeps
find_package(paho.mqtt.c REQUIRED)

add_executable(test_paho_mqtt_c test.c)
target_link_libraries(test_paho_mqtt_c paho.mqtt.c::paho.mqtt.c)

enable_testing()
add_test(NAME test_paho_mqtt_c COMMAND test_paho_mqtt_c)
