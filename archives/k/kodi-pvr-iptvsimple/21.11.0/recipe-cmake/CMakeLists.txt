cmake_minimum_required(VERSION 3.15)
# Standalone build entry for the unmodified pvr.iptvsimple 21.11.0 add-on
# sources.
#
# The upstream CMakeLists.txt is written for the Kodi build system
# (find_package(Kodi REQUIRED) -> build_addon()/addon_version() from the
# kodi-addon-dev distribution, plus the in-tree Findpugixml.cmake /
# Findlzma.cmake pkg-config modules), none of which exists in this
# environment. This file builds the same upstream sources as the Kodi
# binary add-on module against the recipe-provided SDK headers and Conan
# CMakeDeps targets instead.
project(kodi_pvr_iptvsimple LANGUAGES CXX)

# Recipe inputs, set through CMakeToolchain variables in conanfile.py:
#   ADDON_SRC_DIR        - folder holding the upstream sources (src/, LICENSE.md)
#   KODI_DEV_KIT_INCLUDE - kodi-dev-kit tree (provides kodi/ headers)
if(NOT DEFINED ADDON_SRC_DIR)
  set(ADDON_SRC_DIR "${CMAKE_CURRENT_SOURCE_DIR}/..")
endif()
if(NOT DEFINED KODI_DEV_KIT_INCLUDE)
  set(KODI_DEV_KIT_INCLUDE "${CMAKE_CURRENT_SOURCE_DIR}/../kodi-dev-kit")
endif()
set(SRC_DIR "${ADDON_SRC_DIR}/src")

find_package(pugixml CONFIG REQUIRED)
find_package(lzma CONFIG REQUIRED)

# Source list transcribed verbatim from the upstream CMakeLists.txt
# (IPTV_SOURCES).
set(IPTV_SOURCES
    ${SRC_DIR}/addon.cpp
    ${SRC_DIR}/IptvSimple.cpp
    ${SRC_DIR}/iptvsimple/AddonSettings.cpp
    ${SRC_DIR}/iptvsimple/CatchupController.cpp
    ${SRC_DIR}/iptvsimple/Channels.cpp
    ${SRC_DIR}/iptvsimple/ChannelGroups.cpp
    ${SRC_DIR}/iptvsimple/ConnectionManager.cpp
    ${SRC_DIR}/iptvsimple/Epg.cpp
    ${SRC_DIR}/iptvsimple/InstanceSettings.cpp
    ${SRC_DIR}/iptvsimple/Media.cpp
    ${SRC_DIR}/iptvsimple/PlaylistLoader.cpp
    ${SRC_DIR}/iptvsimple/Providers.cpp
    ${SRC_DIR}/iptvsimple/StreamManager.cpp
    ${SRC_DIR}/iptvsimple/data/Channel.cpp
    ${SRC_DIR}/iptvsimple/data/ChannelEpg.cpp
    ${SRC_DIR}/iptvsimple/data/ChannelGroup.cpp
    ${SRC_DIR}/iptvsimple/data/Provider.cpp
    ${SRC_DIR}/iptvsimple/data/EpgEntry.cpp
    ${SRC_DIR}/iptvsimple/data/EpgGenre.cpp
    ${SRC_DIR}/iptvsimple/data/MediaEntry.cpp
    ${SRC_DIR}/iptvsimple/utilities/FileUtils.cpp
    ${SRC_DIR}/iptvsimple/utilities/Logger.cpp
    ${SRC_DIR}/iptvsimple/utilities/SettingsMigration.cpp
    ${SRC_DIR}/iptvsimple/utilities/StreamUtils.cpp
    ${SRC_DIR}/iptvsimple/utilities/WebUtils.cpp
    ${SRC_DIR}/iptvsimple/utilities/WebStreamExtractor.cpp
    ${SRC_DIR}/iptvsimple/utilities/CurlUtils.cpp
    )

# The add-on is a Kodi-host-loaded module (addon.xml declares
# library_linux="pvr.iptvsimple.so"); upstream build_addon() creates it with
# PREFIX "" so the file name matches the addon id.
add_library(pvr.iptvsimple MODULE ${IPTV_SOURCES})
set_target_properties(pvr.iptvsimple PROPERTIES PREFIX "")

target_include_directories(pvr.iptvsimple PRIVATE
                           ${SRC_DIR}
                           ${KODI_DEV_KIT_INCLUDE})

target_compile_features(pvr.iptvsimple PRIVATE cxx_std_17)

# Upstream does add_definitions(-DIPTV_VERSION=${IPTV_VERSION}) with the value
# extracted from pvr.iptvsimple/addon.xml.in (addon_version()). The
# STR() stringification macro used by IptvSimple::GetBackendVersion()
# (std::string(STR(IPTV_VERSION))) is provided by kodi/versions.h itself.
target_compile_definitions(pvr.iptvsimple PRIVATE "IPTV_VERSION=${IPTV_VERSION}")

# OHOS/HarmonyOS platforms do not set the ELF soname flag for shared objects;
# set it explicitly (CI L5a quality gate expects a relative DT_SONAME).
target_link_options(pvr.iptvsimple PRIVATE "-Wl,-soname,pvr.iptvsimple.so")

# pugixml and lzma are consumed as static Conan archives (both PIC); zlib is
# linked against the OHOS system libz.so (the Conan zlib/1.3.1 package is a
# static non-PIC archive — system same-name library, R26 — and cannot be
# linked into a shared module).
target_link_libraries(pvr.iptvsimple PRIVATE
                      pugixml::pugixml
                      lzma::lzma
                      z)

include(GNUInstallDirs)
install(TARGETS pvr.iptvsimple
        LIBRARY DESTINATION ${CMAKE_INSTALL_LIBDIR}
        ARCHIVE DESTINATION ${CMAKE_INSTALL_LIBDIR})
