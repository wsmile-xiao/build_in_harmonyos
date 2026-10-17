cmake_minimum_required(VERSION 3.15)
project(test_libfreefare C)

# 通过 Conan 生成的 CMakeDeps 定位被测包
find_package(libfreefare REQUIRED)

add_executable(test_libfreefare test.c)
target_link_libraries(test_libfreefare libfreefare::libfreefare)

# HarmonyOS 平台专项测试（无设备场景，真实调用 mad/tlv/aid API + 平台特征断言）
add_executable(test_harmonyos_smoke harmonyos_smoke.c)
target_link_libraries(test_harmonyos_smoke libfreefare::libfreefare)

# 上游测试用例移植（test/ 目录纯计算用例，无 Cutter 框架）
add_executable(test_upstream upstream_tests.c)
target_link_libraries(test_upstream libfreefare::libfreefare)

enable_testing()
add_test(NAME test_libfreefare COMMAND test_libfreefare)
add_test(NAME test_harmonyos_smoke COMMAND test_harmonyos_smoke)
add_test(NAME test_upstream COMMAND test_upstream)
