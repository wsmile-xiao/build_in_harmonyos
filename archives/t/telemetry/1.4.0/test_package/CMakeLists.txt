cmake_minimum_required(VERSION 3.18)
project(test_telemetry_consumer CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(telemetry REQUIRED)

# Core library: the telemetry tree API has to be usable from a downstream
# project (real API usage, see test_telemetry.cpp).
add_executable(test_telemetry_consumer test_telemetry.cpp)
target_link_libraries(test_telemetry_consumer PRIVATE telemetry::telemetry)

# HarmonyOS specific test: FUSE 3.0 ABI / 64-bit off_t contract published by
# appFs and DT_SONAME versioned loading of both packaged libraries.
add_executable(test_appfs_ohos test_appfs_ohos.cpp)
target_link_libraries(test_appfs_ohos PRIVATE telemetry::telemetry ${CMAKE_DL_LIBS})

enable_testing()
add_test(NAME test_telemetry_consumer COMMAND test_telemetry_consumer)
add_test(NAME test_appfs_ohos COMMAND test_appfs_ohos)
