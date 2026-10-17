cmake_minimum_required(VERSION 3.15)
# Standalone build entry for the inputstream.rtmp add-on sources.
#
# The upstream CMakeLists.txt needs the Kodi build system
# (find_package(Kodi REQUIRED) -> build_addon(), KODI_INCLUDE_DIR) which does
# not exist in this environment; this file builds the same unmodified sources
# as a shared module against Conan CMakeDeps targets instead.
project(inputstream_rtmp LANGUAGES CXX)

set(SRC_DIR "${CMAKE_CURRENT_SOURCE_DIR}/../src")
# Vendored Kodi C++ add-on headers (kodi-dev-kit), verbatim from
# xbmc 21.3-Omega xbmc/addons/kodi-dev-kit/include/kodi (its kodi/ subtree is
# vendored one level up as kodi-dev-kit/kodi so that <kodi/...> resolves).
set(KODI_DEV_KIT_INCLUDE "${CMAKE_CURRENT_SOURCE_DIR}/../kodi-dev-kit")
# Parent of the Conan librtmp include dir; upstream code uses
# <librtmp/rtmp.h>-style includes while the librtmp package exposes
# include/librtmp itself (value injected from conanfile.generate()).
set(RTMP_INCLUDE_PARENT "" CACHE PATH "Parent dir of the librtmp include dir")

find_package(librtmp CONFIG REQUIRED)
find_package(openssl CONFIG REQUIRED)

# The Conan zlib/1.3.1 package is intentionally built as a static, non-PIC
# archive (system same-name library, R26: "zlib is a system same-name library
# (/lib/libz.so*)"), and a non-PIC archive cannot be linked into a shared
# module on aarch64 ("relocation R_AARCH64_* cannot be used against symbol
# 'z_errmsg'"). The add-on's zlib symbols (pulled in by static librtmp)
# therefore resolve against the OHOS system libz.so: the SDK sysroot ships
# usr/lib/aarch64-linux-ohos/libz.so and the device runtime provides
# /usr/lib/libz.so.1 (DT_NEEDED libz.so.1, resolved at exec).
#
# To keep the static libz.a off the link line, cut librtmp's transitive
# dependency group: Conan CMakeDeps attaches "openssl::openssl;zlib::zlib" to
# the helper interface target librtmp_DEPS_TARGET (consumed through the
# package's per-lib imported targets), so clearing it removes the non-PIC
# libz.a while librtmp's own PIC archive still comes through
# librtmp::librtmp. Everything librtmp needs is linked explicitly below:
# the PIC OpenSSL archives via openssl::openssl and the zlib symbols against
# the system libz.
if(TARGET librtmp_DEPS_TARGET)
    set_property(TARGET librtmp_DEPS_TARGET PROPERTY INTERFACE_LINK_LIBRARIES "")
endif()

add_library(inputstream.rtmp SHARED
            "${SRC_DIR}/RTMPStream.cpp"
            "${SRC_DIR}/timer/Timer.cpp")

target_include_directories(inputstream.rtmp PRIVATE
                           "${SRC_DIR}"
                           "${KODI_DEV_KIT_INCLUDE}"
                           "${RTMP_INCLUDE_PARENT}")

target_compile_features(inputstream.rtmp PRIVATE cxx_std_17)

# The OHOS/HarmonyOS platform module in CMake does not define the soname
# flag (Android-style), so shared libraries come out without DT_SONAME;
# set it explicitly (CI L5a quality gate requires a relative DT_SONAME).
target_link_options(inputstream.rtmp PRIVATE "-Wl,-soname,libinputstream.rtmp.so")

target_link_libraries(inputstream.rtmp PRIVATE
                      librtmp::librtmp
                      openssl::openssl
                      z)

include(GNUInstallDirs)
install(TARGETS inputstream.rtmp
        LIBRARY DESTINATION ${CMAKE_INSTALL_LIBDIR}
        ARCHIVE DESTINATION ${CMAKE_INSTALL_LIBDIR}
        RUNTIME DESTINATION ${CMAKE_INSTALL_BINDIR})
