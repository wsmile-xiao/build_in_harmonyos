cmake_minimum_required(VERSION 3.15)
project(test_kea_hooks CXX)

# find_package() proves the exported Conan target is usable, and the program
# below links against libkea-hooks and calls its API.
find_package(kea-hooks REQUIRED)

add_executable(test_kea_hooks test_kea_hooks.cpp)
target_link_libraries(test_kea_hooks PRIVATE kea-hooks::kea-hooks)
set_target_properties(test_kea_hooks PROPERTIES
    CXX_STANDARD 17
    CXX_STANDARD_REQUIRED ON)

# HarmonyOS-specific test: verifies the packaged artefact carries the OHOS
# aarch64 / musl / libc++ platform ABI signature, that the OHOS loader maps it
# with RTLD_NOW, and that the OHOS-only consumer define the package exports
# (BOOST_SP_NO_PTHREAD_SETCANCELSTATE) reaches the consumer's compile line.
add_executable(test_ohos_platform test_ohos_platform.cpp)
target_link_libraries(test_ohos_platform PRIVATE
    kea-hooks::kea-hooks
    ${CMAKE_DL_LIBS})
set_target_properties(test_ohos_platform PROPERTIES
    CXX_STANDARD 17
    CXX_STANDARD_REQUIRED ON)

enable_testing()
add_test(NAME test_kea_hooks COMMAND test_kea_hooks)
# test_ohos_platform is driven by the Conan test_package: it takes the path of
# the packaged libkea-hooks.so as its only argument, which the recipe resolves
# from the package folder at test time.
