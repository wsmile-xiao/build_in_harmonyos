cmake_minimum_required(VERSION 3.15)
project(libnexstar_test LANGUAGES C)

find_package(libnexstar CONFIG REQUIRED)

add_executable(libnexstar_tests libnexstar_tests.c)
target_link_libraries(libnexstar_tests PRIVATE libnexstar::libnexstar)

enable_testing()
add_test(NAME upstream_celtest COMMAND libnexstar_tests celtest)
add_test(NAME upstream_nexstarctl COMMAND libnexstar_tests nexstarctl)
add_test(NAME upstream_nexstarctl2 COMMAND libnexstar_tests nexstarctl2)
add_test(NAME upstream_get_rade1 COMMAND libnexstar_tests get_rade1)
add_test(NAME upstream_get_rade2 COMMAND libnexstar_tests get_rade2)
add_test(NAME upstream_push_buttons COMMAND libnexstar_tests push_buttons)
add_test(NAME upstream_push_left COMMAND libnexstar_tests push_left)

if(CMAKE_SYSTEM_NAME MATCHES "^(HarmonyOS|OHOS)$")
    add_executable(ohos_platform_test ohos_platform_test.c)
    target_link_libraries(ohos_platform_test PRIVATE libnexstar::libnexstar)
    add_test(NAME harmonyos_aarch64_api COMMAND ohos_platform_test)
endif()
