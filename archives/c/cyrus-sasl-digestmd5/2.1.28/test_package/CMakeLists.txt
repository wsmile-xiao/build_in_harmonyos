cmake_minimum_required(VERSION 3.15)
project(test_cyrus_sasl_digestmd5 C)

# Static-first package: never pick a system libsasl2.so.3 via module mode.
# CONFIG forces Conan's cyrus-sasl-digestmd5-config.cmake (absolute path to
# the packaged library); BUILD_SHARED_LIBS OFF keeps a static default
# consumer fully static so no DT_NEEDED libsasl2.so.3 is baked into
# test_digestmd5 on OHOS.
set(BUILD_SHARED_LIBS OFF)
find_package(cyrus-sasl-digestmd5 REQUIRED CONFIG)

# The DIGEST-MD5 confidentiality layer binds to OpenSSL's DES entry points
# (SASL_DES_CHK -> LIB_DES="-lcrypto", WITH_SSL_DES). test_digestmd5.c
# references those symbols so the link must resolve them through the
# closure the package propagates via cpp_info.requires — it deliberately
# does not include <openssl/des.h>, so no OpenSSL target has to be named
# here (the include directories of the Conan-provided openssl are not
# attached to the imported target for a CMakeDeps consumer).
add_executable(test_digestmd5 test_digestmd5.c)
target_link_libraries(test_digestmd5 PRIVATE
    cyrus-sasl-digestmd5::cyrus-sasl-digestmd5)

enable_testing()
add_test(NAME test_digestmd5 COMMAND test_digestmd5)
