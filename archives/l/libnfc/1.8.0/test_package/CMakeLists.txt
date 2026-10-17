cmake_minimum_required(VERSION 3.15)
project(test_libnfc C)

# Find the package via Conan-generated CMakeDeps
find_package(libnfc REQUIRED)

add_executable(test_libnfc test.c)
target_link_libraries(test_libnfc libnfc::libnfc)

# HarmonyOS 平台专项测试（无设备场景，真实调用 nfc_version/nfc_init/nfc_exit/nfc_list_devices）
add_executable(test_harmonyos_smoke harmonyos_smoke.c)
target_link_libraries(test_harmonyos_smoke libnfc::libnfc)

enable_testing()
add_test(NAME test_libnfc COMMAND test_libnfc)
add_test(NAME test_harmonyos_smoke COMMAND test_harmonyos_smoke)
