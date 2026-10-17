cmake_minimum_required(VERSION 3.16)
project(libdebugutils_test CXX)

enable_testing()
find_package(libdebugutils REQUIRED CONFIG)

add_executable(libdebugutils_test test_libdebugutils.cpp)
target_link_libraries(libdebugutils_test PRIVATE libdebugutils::libdebugutils)
add_test(NAME libdebugutils.consumer COMMAND libdebugutils_test)

if(CMAKE_SYSTEM_NAME MATCHES "^(OHOS|HarmonyOS)$")
    add_executable(libdebugutils_harmonyos_test test_harmonyos_platform.cpp)
    add_test(NAME libdebugutils.harmonyos-platform COMMAND libdebugutils_harmonyos_test)
endif()
