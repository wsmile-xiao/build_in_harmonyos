cmake_minimum_required(VERSION 3.15)
project(test_libfcrypto C)

find_package(libfcrypto REQUIRED CONFIG)

add_executable(test_libfcrypto test_libfcrypto.c)
target_link_libraries(test_libfcrypto PRIVATE libfcrypto::libfcrypto)

# The OHOS-specific consumer is gated by an explicit variable from the
# test_package conanfile (settings.os == "OHOS"): the toolchain's
# CMAKE_SYSTEM_NAME mapping is not something to rely on here.
if(LIBFCRYPTO_BUILD_OHOS_TEST)
    add_executable(test_ohos test_ohos.c)
    target_link_libraries(test_ohos PRIVATE libfcrypto::libfcrypto)
endif()
