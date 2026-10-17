cmake_minimum_required(VERSION 3.15)
project(test_coap C)

# libcoap_DEPS_TARGET references openssl::openssl, but the registry openssl
# config may be absent under that exact name/case in the consumer graph
# (second preflight still fails after package_info.requires + lib/cmake
# removal). Preload the upstream OpenSSL config from the Conan package
# (OpenSSL_DIR/openssl_DIR injected by conan_toolchain, ladybug precedent)
# and bridge the aggregate target BEFORE find_package(libcoap)
# (brpc 1.17.0 protobuf::protobuf bridge precedent).
find_package(OpenSSL CONFIG QUIET)
if(NOT OpenSSL_FOUND)
  find_package(openssl CONFIG QUIET)
endif()
if(NOT TARGET openssl::openssl)
  add_library(openssl::openssl INTERFACE IMPORTED)
  if(TARGET OpenSSL::SSL)
    set_target_properties(openssl::openssl PROPERTIES
      INTERFACE_LINK_LIBRARIES "OpenSSL::SSL;OpenSSL::Crypto")
  elseif(DEFINED LIBCOAP_OPENSSL_SSL_LIB AND DEFINED LIBCOAP_OPENSSL_CRYPTO_LIB)
    set_target_properties(openssl::openssl PROPERTIES
      INTERFACE_LINK_LIBRARIES "${LIBCOAP_OPENSSL_SSL_LIB};${LIBCOAP_OPENSSL_CRYPTO_LIB}")
  endif()
endif()

find_package(libcoap REQUIRED CONFIG)

add_executable(test_coap test_coap.c)
target_link_libraries(test_coap PRIVATE libcoap::coap-3)
