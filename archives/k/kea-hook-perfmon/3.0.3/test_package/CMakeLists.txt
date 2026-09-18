cmake_minimum_required(VERSION 3.15)
project(test_kea_hook_perfmon C)

# The plug-in is dlopen()-ed by the Kea server at runtime, so the exported
# Conan target is interface-only; find_package() proves the package is usable.
find_package(kea-hook-perfmon REQUIRED)

# Consumer-view test: loads the packaged hook and checks the Kea hook contract.
add_executable(test_perfmon_hook test_perfmon_hook.c)
target_link_libraries(test_perfmon_hook PRIVATE
    kea-hook-perfmon::kea-hook-perfmon
    ${CMAKE_DL_LIBS})

# HarmonyOS-specific test: checks the packaged artefact carries the OHOS
# aarch64 / musl / libc++ platform ABI signature and that the OHOS loader can
# map it with RTLD_NOW.
add_executable(test_ohos_platform test_ohos_platform.c)
target_link_libraries(test_ohos_platform PRIVATE
    kea-hook-perfmon::kea-hook-perfmon
    ${CMAKE_DL_LIBS})

enable_testing()
add_test(NAME test_perfmon_hook COMMAND test_perfmon_hook)
add_test(NAME test_ohos_platform COMMAND test_ohos_platform)
