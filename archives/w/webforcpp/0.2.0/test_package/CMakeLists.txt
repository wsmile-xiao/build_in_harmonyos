cmake_minimum_required(VERSION 3.16)
project(test_webforcpp CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(webforcpp REQUIRED CONFIG)
find_package(Threads REQUIRED)
# OpenSSL: try both CMake module (OpenSSL) and Conan config (openssl) names.
# ohpcd openssl/3.5.6 exports openssl::openssl (lowercase) while upstream
# expects OpenSSL::SSL/Crypto. Provide aliases so the same CMakeLists works
# with either package name (CI #51042 fix, aligned with libcoap3/i2pd mapping).
find_package(OpenSSL QUIET)
find_package(openssl QUIET CONFIG)
if(NOT OpenSSL_FOUND AND NOT openssl_FOUND)
  find_package(OpenSSL REQUIRED)
endif()
if(NOT TARGET OpenSSL::SSL AND TARGET openssl::openssl)
  add_library(OpenSSL::SSL ALIAS openssl::openssl)
endif()
if(NOT TARGET OpenSSL::Crypto AND TARGET openssl::openssl)
  add_library(OpenSSL::Crypto ALIAS openssl::openssl)
endif()
if(NOT TARGET OpenSSL::Crypto AND TARGET OpenSSL::SSL)
  add_library(OpenSSL::Crypto ALIAS OpenSSL::SSL)
endif()
if(NOT TARGET OpenSSL::SSL AND TARGET OpenSSL::Crypto)
  add_library(OpenSSL::SSL ALIAS OpenSSL::Crypto)
endif()
find_package(ZLIB QUIET)
find_package(zlib CONFIG QUIET)

add_executable(test_webforcpp test.cpp)
target_link_libraries(test_webforcpp PRIVATE webforcpp::webforcpp OpenSSL::SSL OpenSSL::Crypto Threads::Threads)
# OpenSSL libcrypto on OHOS contains c_zlib.c needing zlib (inflate/deflate).
# Link whichever ZLIB target is provided by CMakeDeps (uppercase via set_property
# or lowercase fallback). Consumers via webforcpp::webforcpp already require
# zlib::zlib but explicit link ensures test_package succeeds even if transitive
# is not propagated in older generators.
if(TARGET ZLIB::ZLIB)
  target_link_libraries(test_webforcpp PRIVATE ZLIB::ZLIB)
endif()
if(TARGET zlib::zlib)
  target_link_libraries(test_webforcpp PRIVATE zlib::zlib)
endif()

enable_testing()
add_test(NAME test_webforcpp COMMAND test_webforcpp)
