cmake_minimum_required(VERSION 3.5)
project(test_ulfius_package C)

find_package(Ulfius 2.7.15 REQUIRED)
# ulfius.h includes <orcania.h>/<yder.h>/<jansson.h>/<microhttpd.h> in its
# public API surface (upstream UlfiusConfig does not re-export them).
find_package(Orcania 2.3.3 REQUIRED)
find_package(Yder 1.4.20 REQUIRED)
find_package(jansson 2.14 REQUIRED)
find_package(libmicrohttpd 1.0.1 REQUIRED)
find_package(gnutls 3.8.10 REQUIRED)
find_package(ZLIB 1.3.1.1 REQUIRED)

add_executable(test_ulfius src/test_ulfius.c)
target_link_libraries(test_ulfius PRIVATE
    $<IF:$<TARGET_EXISTS:Ulfius::Ulfius-static>,Ulfius::Ulfius-static,Ulfius::Ulfius>
    $<IF:$<TARGET_EXISTS:Orcania::Orcania-static>,Orcania::Orcania-static,Orcania::Orcania>
    $<IF:$<TARGET_EXISTS:Yder::Yder-static>,Yder::Yder-static,Yder::Yder>
    jansson::jansson
    libmicrohttpd::libmicrohttpd
    gnutls::gnutls
    $<IF:$<TARGET_EXISTS:ZLIB::ZLIB>,ZLIB::ZLIB,zlib::zlib>)
