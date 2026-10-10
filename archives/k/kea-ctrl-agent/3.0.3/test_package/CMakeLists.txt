cmake_minimum_required(VERSION 3.15)
project(test_kea_ctrl_agent C)

# kea-ctrl-agent is a service binary: importing the package proves a consumer
# can consume it through the generated CMake config.
find_package(kea-ctrl-agent REQUIRED)

# HarmonyOS-specific test #1: the packaged executable carries the OHOS aarch64 /
# musl / libc++ platform ABI signature.
add_executable(test_ohos_platform test_ohos_platform.c)
target_link_libraries(test_ohos_platform PRIVATE
    kea-ctrl-agent::kea-ctrl-agent
    ${CMAKE_DL_LIBS})

# HarmonyOS-specific test #2: the packaged Kea runtime closure (libkea-*.so*)
# resolves under the OHOS loader and the agent really runs.
add_executable(test_ohos_runtime test_ohos_runtime.c)
target_link_libraries(test_ohos_runtime PRIVATE
    kea-ctrl-agent::kea-ctrl-agent
    ${CMAKE_DL_LIBS})

enable_testing()
add_test(NAME test_ohos_platform COMMAND test_ohos_platform)
add_test(NAME test_ohos_runtime COMMAND test_ohos_runtime)
