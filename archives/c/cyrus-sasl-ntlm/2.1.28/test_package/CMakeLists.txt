cmake_minimum_required(VERSION 3.15)
project(test_cyrus_sasl_ntlm C)

# Static-only package: never pick a system libsasl2.so.3 via module mode.
# CONFIG forces Conan's cyrus-sasl-ntlm-config.cmake (absolute path to
# libsasl2.a); BUILD_SHARED_LIBS OFF keeps the consumer fully static so
# no DT_NEEDED libsasl2.so.3 is baked into test_ntlm on OHOS.
set(BUILD_SHARED_LIBS OFF)
find_package(cyrus-sasl-ntlm REQUIRED CONFIG)

add_executable(test_ntlm test_ntlm.c)
target_link_libraries(test_ntlm PRIVATE cyrus-sasl-ntlm::cyrus-sasl-ntlm)

enable_testing()
add_test(NAME test_ntlm COMMAND test_ntlm)
