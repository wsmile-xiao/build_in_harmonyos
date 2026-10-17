# Source paths are relative to the upstream tarball root because this
# CMakeLists.txt is copied to <source>/recipe-cmake/ but CMake resolves
# paths relative to CMAKE_CURRENT_SOURCE_DIR of this file.
cmake_minimum_required(VERSION 3.15)
project(kodiplatform VERSION 21.2 LANGUAGES CXX)

# Conan CMakeDeps provides both dependencies:
#   tinyxml/2.6.2     -> tinyxml-config.cmake, target tinyxml::tinyxml
#   p8-platform/2.1.0 -> p8-platform-config.cmake, target p8-platform::p8-platform
find_package(tinyxml CONFIG REQUIRED)
find_package(p8-platform CONFIG REQUIRED)

# Version numbers mirror the upstream CMakeLists.txt, which takes them from
# the Kodi application that the add-on SDK is built against (kodi 21.2 "Omega"
# is the current stable series at the time of the kodiplatform-20250416 tag).
set(kodiplatform_VERSION_MAJOR 21)
set(kodiplatform_VERSION_MINOR 2)
set(kodiplatform_VERSION_PATCH 0)

add_library(kodiplatform ${CMAKE_CURRENT_SOURCE_DIR}/../src/util/XMLUtils.cpp)
set_target_properties(kodiplatform PROPERTIES
    VERSION ${kodiplatform_VERSION_MAJOR}.${kodiplatform_VERSION_MINOR}.${kodiplatform_VERSION_PATCH}
    SOVERSION ${kodiplatform_VERSION_MAJOR}
    POSITION_INDEPENDENT_CODE ON)

target_include_directories(kodiplatform PUBLIC
    $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/../src>
    $<INSTALL_INTERFACE:include>)

target_link_libraries(kodiplatform PUBLIC tinyxml::tinyxml p8-platform::p8-platform)

# XMLUtils.h includes <tinyxml.h> and <p8-platform/util/StringUtils.h> directly,
# both header paths propagate transitively through the linked targets above.

include(GNUInstallDirs)

install(TARGETS kodiplatform
    ARCHIVE DESTINATION ${CMAKE_INSTALL_LIBDIR}
    LIBRARY DESTINATION ${CMAKE_INSTALL_LIBDIR}
    RUNTIME DESTINATION ${CMAKE_INSTALL_BINDIR})

# Same header location as the upstream CMakeLists.txt
# (include/kodi/util/XMLUtils.h), so downstream Kodi add-ons keep their
# `#include <kodi/util/XMLUtils.h>` includes unchanged.
install(FILES ${CMAKE_CURRENT_SOURCE_DIR}/../src/util/XMLUtils.h
    DESTINATION ${CMAKE_INSTALL_INCLUDEDIR}/kodi/util)

# pkg-config file for consumers that use pkg_check_modules instead of CMake
configure_file(kodiplatform.pc.in kodiplatform.pc @ONLY)
install(FILES ${CMAKE_CURRENT_BINARY_DIR}/kodiplatform.pc
    DESTINATION ${CMAKE_INSTALL_LIBDIR}/pkgconfig)
