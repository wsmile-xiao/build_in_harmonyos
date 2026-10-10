cmake_minimum_required(VERSION 3.15)
project(test_isc_kea CXX)

# find_package() proves the exported Conan target is usable, and the programs
# below link against the packaged libkea-* libraries and call their API.
find_package(isc-kea REQUIRED)

add_executable(test_isc_kea test_isc_kea.cpp)
target_link_libraries(test_isc_kea PRIVATE isc-kea::isc-kea)
set_target_properties(test_isc_kea PROPERTIES
    CXX_STANDARD 17
    CXX_STANDARD_REQUIRED ON)

# HarmonyOS-specific test: verifies the packaged artefacts carry the OHOS
# aarch64 / musl / libc++ platform ABI signature, that the OHOS loader maps
# them with RTLD_NOW, and that the OHOS-only consumer define the package
# exports (BOOST_SP_NO_PTHREAD_SETCANCELSTATE) reaches the consumer's compile
# line.
add_executable(test_ohos_platform test_ohos_platform.cpp)
target_link_libraries(test_ohos_platform PRIVATE
    isc-kea::isc-kea
    ${CMAKE_DL_LIBS})
set_target_properties(test_ohos_platform PROPERTIES
    CXX_STANDARD 17
    CXX_STANDARD_REQUIRED ON)

enable_testing()
add_test(NAME test_isc_kea COMMAND test_isc_kea)
# test_ohos_platform is driven by the Conan test_package: it takes the path of
# a packaged libkea-*.so as its only argument, which the recipe resolves from
# the package folder at test time.
