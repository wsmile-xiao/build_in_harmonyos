cmake_minimum_required(VERSION 3.15)
project(test_kea_hook_pgsql C)

# The plug-in is dlopen()-ed by the Kea server at runtime, so the exported
# Conan target is interface-only; find_package() proves the package is usable.
find_package(kea-hook-pgsql REQUIRED)

add_executable(test_pgsql_hook test_pgsql_hook.c)
target_link_libraries(test_pgsql_hook PRIVATE
    kea-hook-pgsql::kea-hook-pgsql
    ${CMAKE_DL_LIBS})

# HarmonyOS-specific test: checks the packaged artefact carries the OHOS
# aarch64 / musl / libc++ platform ABI signature and links libpq, that the
# OHOS loader can map it with RTLD_NOW and that the pgsql hook callouts
# resolve on OHOS.
add_executable(test_ohos_platform test_ohos_platform.c)
target_link_libraries(test_ohos_platform PRIVATE
    kea-hook-pgsql::kea-hook-pgsql
    ${CMAKE_DL_LIBS})

enable_testing()
add_test(NAME test_pgsql_hook COMMAND test_pgsql_hook)
add_test(NAME test_ohos_platform COMMAND test_ohos_platform)
