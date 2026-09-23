cmake_minimum_required(VERSION 3.15)
project(test_zycore_c C)

find_package(zycore CONFIG REQUIRED)

add_executable(test_zycore_c test.c)
target_link_libraries(test_zycore_c PRIVATE Zycore::Zycore)

# HarmonyOS 专项测试：通过公开 API 验证 OHOS 平台行为（Thread TLS/String/Vector）
add_executable(test_zycore_ohos ohos_test.c)
target_link_libraries(test_zycore_ohos PRIVATE Zycore::Zycore)