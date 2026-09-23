cmake_minimum_required(VERSION 3.15)
project(test_wolfmqtt C)

# Find the package via Conan-generated CMakeDeps
find_package(wolfmqtt REQUIRED)
find_package(wolfssl REQUIRED)

add_executable(test_wolfmqtt test.c)
target_link_libraries(test_wolfmqtt wolfmqtt::wolfmqtt wolfssl::wolfssl)

# wolfmqtt public headers include <wolfssl/options.h> (ENABLE_MQTT_TLS build).
# The published wolfssl package ships empty cpp_info.include_dirs, so add its
# include dir explicitly from the CMakeDeps package-folder variable.
target_include_directories(test_wolfmqtt PRIVATE
    ${wolfmqtt_PACKAGE_FOLDER_RELEASE}/include
    ${wolfssl_PACKAGE_FOLDER_RELEASE}/include)
target_compile_definitions(test_wolfmqtt PRIVATE ENABLE_MQTT_TLS)

enable_testing()
add_test(NAME test_wolfmqtt COMMAND test_wolfmqtt)
