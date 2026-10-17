cmake_minimum_required(VERSION 3.15)
project(test_micro_ecc C)

find_package(micro-ecc REQUIRED CONFIG)

add_executable(test_micro_ecc test.c)
target_link_libraries(test_micro_ecc PRIVATE micro-ecc::micro-ecc)

# HarmonyOS 专项测试（OHOS arm64 平台识别 + 全曲线 ECDH/ECDSA）
add_executable(test_micro_ecc_ohos test_ohos.c)
target_link_libraries(test_micro_ecc_ohos PRIVATE micro-ecc::micro-ecc)

include(CTest)
if(BUILD_TESTING)
    add_test(NAME test_micro_ecc COMMAND test_micro_ecc)
    add_test(NAME test_micro_ecc_ohos COMMAND test_micro_ecc_ohos)
endif()