# CMake wrapper for librtpi 1.0.0 (exported by the Conan recipe).
#
# Upstream 1.0.0 ships an autotools build only (configure.ac, no generated
# configure) and requires `autoreconf --install` plus the autoconf-archive
# macro AX_CXX_COMPILE_STDCXX_11.  The OHOS PC image ships no
# autoconf/automake/libtool (verified 2026-09-18), so the Conan recipe drives
# this wrapper instead.  It reproduces the upstream build exactly:
#   - sources:   src/pi_mutex.c src/pi_cond.c
#   - library:   librtpi, version-info 1:0:0 (soname librtpi.so.1)
#   - headers:   nobase_include_HEADERS = rtpi.h rtpi_internal.h
#               rtpi/condition_variable.hpp rtpi/mutex.hpp
#   - the upstream --disable-cancellation switch maps to
#     RTPI_ENABLE_CANCELLATION=OFF (omit -DENABLE_CANCELLATION)
cmake_minimum_required(VERSION 3.10)
project(librtpi LANGUAGES C VERSION 1.0.0)

include(GNUInstallDirs)

option(RTPI_ENABLE_CANCELLATION
       "Enable pthread cancellation support (upstream default: ON)" ON)
option(BUILD_SHARED_LIBS "Build shared librtpi instead of static" OFF)

set(RTPI_SOURCES src/pi_mutex.c src/pi_cond.c)
set(RTPI_HEADERS
    src/rtpi.h
    src/rtpi_internal.h
    src/rtpi/condition_variable.hpp
    src/rtpi/mutex.hpp)

add_library(librtpi ${RTPI_SOURCES})

set_target_properties(librtpi PROPERTIES
    OUTPUT_NAME rtpi
    VERSION ${PROJECT_VERSION}
    SOVERSION ${PROJECT_VERSION_MAJOR}
    C_STANDARD 11
    POSITION_INDEPENDENT_CODE ON)

target_include_directories(librtpi PUBLIC
    $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/src>)

if(RTPI_ENABLE_CANCELLATION)
    target_compile_definitions(librtpi PRIVATE ENABLE_CANCELLATION)
endif()

install(TARGETS librtpi
    RUNTIME DESTINATION ${CMAKE_INSTALL_BINDIR}
    LIBRARY DESTINATION ${CMAKE_INSTALL_LIBDIR}
    ARCHIVE DESTINATION ${CMAKE_INSTALL_LIBDIR})
install(FILES src/rtpi.h src/rtpi_internal.h
        DESTINATION ${CMAKE_INSTALL_INCLUDEDIR})
install(FILES src/rtpi/condition_variable.hpp src/rtpi/mutex.hpp
        DESTINATION ${CMAKE_INSTALL_INCLUDEDIR}/rtpi)
