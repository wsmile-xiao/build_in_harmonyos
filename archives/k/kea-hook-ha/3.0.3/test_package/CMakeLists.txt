cmake_minimum_required(VERSION 3.15)
project(test_kea_hook_ha C)

# The plug-in is dlopen()-ed by the Kea server at runtime, so the exported
# Conan target is interface-only; find_package() proves the package is usable.
find_package(kea-hook-ha REQUIRED)

# Consumer-view test: loads the packaged hook and checks the Kea hook contract.
add_executable(test_ha_hook test_ha_hook.c)
target_link_libraries(test_ha_hook PRIVATE
    kea-hook-ha::kea-hook-ha
    ${CMAKE_DL_LIBS})

# HarmonyOS-specific test #1: the packaged artefact carries the OHOS aarch64 /
# musl / libc++ platform ABI signature and the OHOS loader can map it.
add_executable(test_ohos_platform test_ohos_platform.c)
target_link_libraries(test_ohos_platform PRIVATE
    kea-hook-ha::kea-hook-ha
    ${CMAKE_DL_LIBS})

# HarmonyOS-specific test #2: the whole packaged Kea runtime closure (20
# libraries) is resolvable by the OHOS loader at run time.
add_executable(test_ohos_runtime test_ohos_runtime.c)
target_link_libraries(test_ohos_runtime PRIVATE
    kea-hook-ha::kea-hook-ha
    ${CMAKE_DL_LIBS})

# No CTest entries are registered here on purpose: every check requires the
# path of the packaged plug-in (and the Conan runtime library search path) as
# an argument, which only the Conan test_package runner provides -- see
# conanfile.py test(), which executes the three binaries directly.
