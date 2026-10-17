# Standalone build entry for the unmodified upstream sources of
# audioencoder.wav 21.0.2-Omega on OHOS.
#
# The upstream CMakeLists.txt needs find_package(Kodi) + build_addon()
# from the kodi-addon-dev distribution (not packaged on the ohpcd registry).
# This entry builds the same sources with the recipe-provided Kodi SDK
# include tree, replicating the parts of the upstream flow that matter:
#   - module target named audioencoder.wav with PREFIX "" (build_addon),
#     producing audioencoder.wav.so — the file name the add-on's addon.xml
#     expects as library_filename
#   - upstream DEPLIBS is empty: the WAV encoder has no codec libraries, it
#     writes PCM headers/data through the host-provided VFS stream only
#   - POSITION_INDEPENDENT_CODE (build_addon sets it for the shared module;
#     a MODULE target compiles its sources with -fPIC automatically)
# Upstream sources are consumed unmodified from ../src (ADDON_SRC_DIR).
#
# An audio encoder has no GL/EGL render path, so — unlike the screensaver
# add-on — no HAS_GLES / GLESv3 / EGL setup is needed here.
cmake_minimum_required(VERSION 3.5)
project(audioencoder.wav C CXX)

# Recipe inputs, set through CMakeToolchain variables in conanfile.py:
#   ADDON_SRC_DIR        - folder holding the upstream sources
#                          (src/, audioencoder.wav/, LICENSE.md)
#   KODI_SDK_INCLUDE_DIR - kodi-dev-kit include tree (provides kodi/ headers)

set(WAV_ADDON_SOURCES ${ADDON_SRC_DIR}/src/EncoderWav.cpp)

add_library(${PROJECT_NAME} MODULE ${WAV_ADDON_SOURCES})
set_target_properties(${PROJECT_NAME} PROPERTIES PREFIX "")

target_include_directories(${PROJECT_NAME} PRIVATE
                           ${ADDON_SRC_DIR}
                           ${KODI_SDK_INCLUDE_DIR})
target_compile_features(${PROJECT_NAME} PRIVATE cxx_std_17)
