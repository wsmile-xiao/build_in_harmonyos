cmake_minimum_required(VERSION 3.15)
project(test_kea_hook_legal_log C)

# The plug-in is dlopen()-ed by the Kea server at runtime, so the exported
# Conan target is interface-only; find_package() proves the package is usable.
find_package(kea-hook-legal-log REQUIRED)

# Consumer-view test: loads the packaged hook and checks the Kea hook contract.
add_executable(test_legal_log_hook test_legal_log_hook.c)
target_link_libraries(test_legal_log_hook PRIVATE
    kea-hook-legal-log::kea-hook-legal-log
    ${CMAKE_DL_LIBS})

# HarmonyOS-specific test #1: the packaged artefact carries the OHOS aarch64 /
# musl / libc++ platform ABI signature and the OHOS loader can map it.
add_executable(test_ohos_platform test_ohos_platform.c)
target_link_libraries(test_ohos_platform PRIVATE
    kea-hook-legal-log::kea-hook-legal-log
    ${CMAKE_DL_LIBS})

# HarmonyOS-specific test #2: the whole packaged Kea runtime closure (20
# libraries) is resolvable by the OHOS loader at run time.
add_executable(test_ohos_runtime test_ohos_runtime.c)
target_link_libraries(test_ohos_runtime PRIVATE
    kea-hook-legal-log::kea-hook-legal-log
    ${CMAKE_DL_LIBS})

enable_testing()
add_test(NAME test_legal_log_hook COMMAND test_legal_log_hook)
add_test(NAME test_ohos_platform COMMAND test_ohos_platform)
add_test(NAME test_ohos_runtime COMMAND test_ohos_runtime)
