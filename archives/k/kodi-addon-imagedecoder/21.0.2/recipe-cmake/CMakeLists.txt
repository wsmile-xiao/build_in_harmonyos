# Standalone build entry for the unmodified upstream sources of
# imagedecoder.mpo 21.0.2-Omega on OHOS.
#
# The upstream CMakeLists.txt needs find_package(Kodi) + build_addon()
# from the kodi-addon-dev distribution (not packaged on the ohpcd registry).
# This entry builds the same sources with the recipe-provided Kodi SDK
# include tree, replicating the parts of the upstream flow that matter:
#   - module target named imagedecoder.mpo with PREFIX "" (build_addon)
#   - the vendored libmpo (lib/libmpo, upstream builds it as mpo_static via
#     its own CMakeLists and links it through DEPLIBS) and TinyEXIF
#     (lib/TinyEXIF, listed in upstream MPO_SOURCES) compiled into the same
#     module — all sources stay unmodified
#   - POSITION_INDEPENDENT_CODE (build_addon sets it for the shared module;
#     a MODULE target compiles its sources with -fPIC automatically)
# Upstream sources are consumed unmodified from ../src (ADDON_SRC_DIR).
#
# An image decoder has no GL/EGL render path (it only writes decoded pixels
# into the host-provided buffer), so — unlike the screensaver add-on — no
# HAS_GLES / GLESv3 / EGL setup is needed here.
cmake_minimum_required(VERSION 3.5)
project(imagedecoder.mpo C CXX)

# Recipe inputs, set through CMakeToolchain variables in conanfile.py:
#   ADDON_SRC_DIR        - folder holding the upstream sources
#                          (src/, lib/, LICENSE.md)
#   KODI_SDK_INCLUDE_DIR - kodi-dev-kit include tree (provides kodi/ headers)

set(MPO_ADDON_SOURCES ${ADDON_SRC_DIR}/src/MPOPicture.cpp)
set(MPO_VENDORED_SOURCES
                    ${ADDON_SRC_DIR}/lib/libmpo/src/cmpo.c
                    ${ADDON_SRC_DIR}/lib/libmpo/src/dmpo.c
                    ${ADDON_SRC_DIR}/lib/libmpo/src/mpo.c
                    ${ADDON_SRC_DIR}/lib/libmpo/src/mpodatasrc.c
                    ${ADDON_SRC_DIR}/lib/TinyEXIF/TinyEXIF.cpp)

find_package(libjpeg-turbo CONFIG REQUIRED)
find_package(tinyxml2 CONFIG REQUIRED)

add_library(${PROJECT_NAME} MODULE ${MPO_ADDON_SOURCES} ${MPO_VENDORED_SOURCES})
set_target_properties(${PROJECT_NAME} PROPERTIES PREFIX "")

target_include_directories(${PROJECT_NAME} PRIVATE
                           ${ADDON_SRC_DIR}
                           ${ADDON_SRC_DIR}/lib/libmpo/include
                           ${KODI_SDK_INCLUDE_DIR})
target_compile_features(${PROJECT_NAME} PRIVATE cxx_std_17)
target_link_libraries(${PROJECT_NAME} PRIVATE
                      libjpeg-turbo::libjpeg-turbo
                      tinyxml2::tinyxml2)
