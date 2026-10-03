cmake_minimum_required(VERSION 3.15)
project(test_kea_hook_ddns_tuning C)

# The plug-in is dlopen()-ed by the Kea server at runtime, so the exported
# Conan target is interface-only; find_package() proves the package is usable.
find_package(kea-hook-ddns-tuning REQUIRED)

# Consumer-view test: loads the packaged hook and checks the Kea hook contract.
add_executable(test_ddns_tuning_hook test_ddns_tuning_hook.c)
target_link_libraries(test_ddns_tuning_hook PRIVATE
    kea-hook-ddns-tuning::kea-hook-ddns-tuning
    ${CMAKE_DL_LIBS})

# HarmonyOS-specific test #1: the packaged artefact carries the OHOS aarch64 /
# musl / libc++ platform ABI signature and the OHOS loader can map it.
add_executable(test_ohos_platform test_ohos_platform.c)
target_link_libraries(test_ohos_platform PRIVATE
    kea-hook-ddns-tuning::kea-hook-ddns-tuning
    ${CMAKE_DL_LIBS})

# HarmonyOS-specific test #2: the whole packaged Kea runtime closure (20
# libraries) is resolvable by the OHOS loader at run time.
add_executable(test_ohos_runtime test_ohos_runtime.c)
target_link_libraries(test_ohos_runtime PRIVATE
    kea-hook-ddns-tuning::kea-hook-ddns-tuning
    ${CMAKE_DL_LIBS})

enable_testing()
add_test(NAME test_ddns_tuning_hook COMMAND test_ddns_tuning_hook)
add_test(NAME test_ohos_platform COMMAND test_ohos_platform)
add_test(NAME test_ohos_runtime COMMAND test_ohos_runtime)
