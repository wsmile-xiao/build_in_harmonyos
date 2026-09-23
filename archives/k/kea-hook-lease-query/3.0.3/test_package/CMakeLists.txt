cmake_minimum_required(VERSION 3.15)
project(test_kea_hook_lease_query C)

# The plug-in is dlopen()-ed by the Kea server at runtime, so the exported
# Conan target is interface-only; find_package() proves the package is usable.
find_package(kea-hook-lease-query REQUIRED)

add_executable(test_lease_query_hook test_lease_query_hook.c)
target_link_libraries(test_lease_query_hook PRIVATE
    kea-hook-lease-query::kea-hook-lease-query
    ${CMAKE_DL_LIBS})

# HarmonyOS-specific test: the packaged artefact carries the OHOS aarch64 /
# musl / libc++ platform ABI signature and the OHOS loader can map it.
add_executable(test_ohos_platform test_ohos_platform.c)
target_link_libraries(test_ohos_platform PRIVATE
    kea-hook-lease-query::kea-hook-lease-query
    ${CMAKE_DL_LIBS})

enable_testing()
add_test(NAME test_lease_query_hook COMMAND test_lease_query_hook)
add_test(NAME test_ohos_platform COMMAND test_ohos_platform)
