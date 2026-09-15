cmake_minimum_required(VERSION 3.15)
project(test_cyrus_sasl_gssapiv2 C)

# Static-first package: never pick a system libsasl2.so.3 via module mode.
# CONFIG forces Conan's cyrus-sasl-gssapiv2-config.cmake (absolute path to
# the packaged library); BUILD_SHARED_LIBS OFF keeps a static default
# consumer fully static so no DT_NEEDED libsasl2.so.3 is baked into
# test_gssapiv2 on OHOS.
set(BUILD_SHARED_LIBS OFF)
find_package(cyrus-sasl-gssapiv2 REQUIRED CONFIG)

add_executable(test_gssapiv2 test_gssapiv2.c)
target_link_libraries(test_gssapiv2 PRIVATE cyrus-sasl-gssapiv2::cyrus-sasl-gssapiv2)

enable_testing()
add_test(NAME test_gssapiv2 COMMAND test_gssapiv2)
