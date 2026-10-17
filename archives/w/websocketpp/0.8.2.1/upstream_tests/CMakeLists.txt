# Upstream websocketpp test suite harness (replaces the Python-2-only SCons
# build, which also requires a prebuilt Boost stage tree that Conan-based
# environments do not provide).
#
# The binary list mirrors SConstruct's to_test directories and the per-dir
# SConscript programs exactly (the *_boost flavor; the *_stl duplicates of the
# same sources are intentionally not rebuilt).  Sources that upstream itself
# does not build are intentionally absent here:
#   - test/message_buffer/pool.cpp        (targets pre-0.8.2 processor API)
#   - test/transport/hybi_util.cpp        (includes ../../src/..., gone since 0.3.x)
#   - test/processors/parser_perf.cpp     (manual perf tool, not a unit test)
#
# Upstream links 'z' for the processors/extension tests and ssl+crypto for the
# asio/endpoint/integration tests; this harness links OpenSSL + ZLIB + Threads
# to every binary, which is a superset and therefore safe.
#
# Boost is consumed header-only:
#   - Boost.Test via <boost/test/included/unit_test.hpp> (the boost package in
#     this repo ships no libboost_unit_test_framework), enabled by patch 0004.
#   - websocketpp itself resolves memory/functional/random/thread to std::
#     under -std=c++17 (common/cpp11.hpp), so no compiled Boost libs are needed.

cmake_minimum_required(VERSION 3.15)
project(websocketpp_upstream_tests CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

enable_testing()

# websocketpp source root (parent of this harness directory)
get_filename_component(WSPP_ROOT "${CMAKE_CURRENT_SOURCE_DIR}/.." ABSOLUTE)

find_package(Threads REQUIRED)

# Boost and OpenSSL arrive as absolute paths from the recipe (dependency
# cpp_info), deliberately bypassing find_package/CMakeDeps naming.
include_directories("${WSPP_ROOT}" "${WSPP_BOOST_INCLUDE}" "${WSPP_OPENSSL_INCLUDE}")

find_library(WSPP_SSL_LIB    NAMES ssl    HINTS "${WSPP_OPENSSL_LIBDIR}" REQUIRED)
find_library(WSPP_CRYPTO_LIB NAMES crypto HINTS "${WSPP_OPENSSL_LIBDIR}" REQUIRED)

# zlib is the platform one (OHOS SDK sysroot), like upstream SCons linking 'z'
find_package(ZLIB)
if(NOT ZLIB_FOUND)
    find_path(ZLIB_INCLUDE_DIR NAMES zlib.h
              HINTS ${CMAKE_CXX_IMPLICIT_INCLUDE_DIRECTORIES})
    find_library(ZLIB_LIBRARY NAMES z
                 HINTS ${CMAKE_CXX_IMPLICIT_LINK_DIRECTORIES})
    if(ZLIB_INCLUDE_DIR AND ZLIB_LIBRARY)
        set(ZLIB_FOUND TRUE)
        if(NOT TARGET ZLIB::ZLIB)
            add_library(ZLIB::ZLIB UNKNOWN IMPORTED)
            set_target_properties(ZLIB::ZLIB PROPERTIES
                IMPORTED_LOCATION "${ZLIB_LIBRARY}"
                INTERFACE_INCLUDE_DIRECTORIES "${ZLIB_INCLUDE_DIR}")
        endif()
    endif()
endif()

set(WSPP_TEST_LIBS "${WSPP_SSL_LIB}" "${WSPP_CRYPTO_LIB}" Threads::Threads)
if(ZLIB_FOUND)
    list(APPEND WSPP_TEST_LIBS ZLIB::ZLIB)
else()
    message(WARNING "ZLIB not found: the 3 permessage-deflate upstream tests will be skipped")
endif()

function(wspp_test name)
    add_executable(${name} ${ARGN})
    # -O0: these are logic tests; keeps the 31-binary suite fast in CI
    # (upstream's own SCons release build used -O1 for the same purpose).
    target_compile_options(${name} PRIVATE -O0)
    target_link_libraries(${name} PRIVATE ${WSPP_TEST_LIBS})
    add_test(NAME ${name} COMMAND ${name} --report_level=short)
endfunction()

# test/utility
wspp_test(test_uri            "${WSPP_ROOT}/test/utility/uri.cpp")
wspp_test(test_utility        "${WSPP_ROOT}/test/utility/utilities.cpp")
wspp_test(test_frame          "${WSPP_ROOT}/test/utility/frame.cpp")
wspp_test(test_close          "${WSPP_ROOT}/test/utility/close.cpp")
wspp_test(test_sha1           "${WSPP_ROOT}/test/utility/sha1.cpp")
wspp_test(test_error          "${WSPP_ROOT}/test/utility/error.cpp")

# test/http
wspp_test(test_http           "${WSPP_ROOT}/test/http/parser.cpp")

# test/logger
wspp_test(logger_basic        "${WSPP_ROOT}/test/logger/basic.cpp")

# test/random
wspp_test(test_random_none    "${WSPP_ROOT}/test/random/none.cpp")
wspp_test(test_random_device  "${WSPP_ROOT}/test/random/random_device.cpp")

# test/processors (hybi13 + extension_permessage_compress need zlib, like upstream)
wspp_test(test_processor      "${WSPP_ROOT}/test/processors/processor.cpp")
wspp_test(test_hybi08         "${WSPP_ROOT}/test/processors/hybi08.cpp")
wspp_test(test_hybi07         "${WSPP_ROOT}/test/processors/hybi07.cpp")
wspp_test(test_hybi00         "${WSPP_ROOT}/test/processors/hybi00.cpp")

# test/extension
wspp_test(test_extension      "${WSPP_ROOT}/test/extension/extension.cpp")

# test/message_buffer
wspp_test(test_message        "${WSPP_ROOT}/test/message_buffer/message.cpp")
wspp_test(test_alloc          "${WSPP_ROOT}/test/message_buffer/alloc.cpp")

# test/transport/iostream
wspp_test(test_iostream_base       "${WSPP_ROOT}/test/transport/iostream/base.cpp")
wspp_test(test_iostream_connection "${WSPP_ROOT}/test/transport/iostream/connection.cpp")
wspp_test(test_iostream_endpoint   "${WSPP_ROOT}/test/transport/iostream/endpoint.cpp")

# test/transport/asio
wspp_test(test_asio_base      "${WSPP_ROOT}/test/transport/asio/base.cpp")
wspp_test(test_asio_timers    "${WSPP_ROOT}/test/transport/asio/timers.cpp")
wspp_test(test_asio_security  "${WSPP_ROOT}/test/transport/asio/security.cpp")

# test/roles
wspp_test(test_client         "${WSPP_ROOT}/test/roles/client.cpp")
wspp_test(test_server         "${WSPP_ROOT}/test/roles/server.cpp")

# test/endpoint
wspp_test(test_endpoint       "${WSPP_ROOT}/test/endpoint/endpoint.cpp")

# test/connection (two translation units upstream)
wspp_test(test_connection     "${WSPP_ROOT}/test/connection/connection.cpp"
                              "${WSPP_ROOT}/test/connection/connection_tu2.cpp")

# test/transport (end-to-end integration)
wspp_test(test_integration    "${WSPP_ROOT}/test/transport/integration.cpp")

# zlib-dependent tests (upstream links 'z' for these)
if(ZLIB_FOUND)
    wspp_test(test_hybi13                   "${WSPP_ROOT}/test/processors/hybi13.cpp")
    wspp_test(test_extension_permessage_compress
                                            "${WSPP_ROOT}/test/processors/extension_permessage_compress.cpp")
    wspp_test(test_permessage_deflate       "${WSPP_ROOT}/test/extension/permessage_deflate.cpp")
else()
    message(WARNING "ZLIB not found: skipping 3 permessage-deflate upstream tests")
endif()
