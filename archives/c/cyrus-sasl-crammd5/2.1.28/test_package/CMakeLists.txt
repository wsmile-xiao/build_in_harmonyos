cmake_minimum_required(VERSION 3.15)
project(test_cyrus_sasl_crammd5 C)

# Static-only package: never pick a system libsasl2.so.3 via module mode.
# CONFIG forces Conan's cyrus-sasl-crammd5-config.cmake (absolute path to
# libsasl2.a); BUILD_SHARED_LIBS OFF keeps the consumer fully static so no
# DT_NEEDED libsasl2.so.3 is baked into test_crammd5 on OHOS.
set(BUILD_SHARED_LIBS OFF)
find_package(cyrus-sasl-crammd5 REQUIRED CONFIG)

add_executable(test_crammd5 test_crammd5.c)
target_link_libraries(test_crammd5 PRIVATE cyrus-sasl-crammd5::cyrus-sasl-crammd5)

enable_testing()
add_test(NAME test_crammd5 COMMAND test_crammd5)
