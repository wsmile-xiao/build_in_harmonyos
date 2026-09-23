cmake_minimum_required(VERSION 3.15)
project(test_cyrus_sasl_login C)

# Static-only package: never pick a system libsasl2.so.3 via module mode.
# CONFIG forces Conan's cyrus-sasl-login-config.cmake (absolute path to
# libsasl2.a); BUILD_SHARED_LIBS OFF keeps the consumer fully static so
# no DT_NEEDED libsasl2.so.3 is baked into test_login on OHOS.
set(BUILD_SHARED_LIBS OFF)
find_package(cyrus-sasl-login REQUIRED CONFIG)

add_executable(test_login test_login.c)
target_link_libraries(test_login PRIVATE cyrus-sasl-login::cyrus-sasl-login)

enable_testing()
add_test(NAME test_login COMMAND test_login)
