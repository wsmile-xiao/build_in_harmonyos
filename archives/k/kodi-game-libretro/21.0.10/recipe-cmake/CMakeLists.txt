# Standalone build entry for the unmodified upstream sources of
# game.libretro 21.0.10-Omega on OHOS.
#
# The upstream CMakeLists.txt needs find_package(Kodi) + build_addon()
# from the kodi-addon-dev distribution (not packaged on the ohpcd registry).
# This entry builds the same sources with the recipe-provided Kodi SDK
# include tree, replicating the parts of the upstream flow that matter:
#   - module target named game.libretro with PREFIX "" (build_addon), i.e.
#     the exact library filename addon.xml's library_filename expects
#   - the upstream dependency closure: registry tinyxml + vendored
#     rcheevos static library (upstream depends source list and
#     -DRC_DISABLE_LUA, built with POSITION_INDEPENDENT_CODE like the
#     upstream ExternalProject) + header-only libretro-common
#   - POSITION_INDEPENDENT_CODE for the shared module (build_addon sets it)
# Upstream sources are consumed unmodified from ${ADDON_SRC_DIR}.
cmake_minimum_required(VERSION 3.5)
project(game.libretro C CXX)

# Recipe inputs, set through CMakeToolchain variables in conanfile.py:
#   ADDON_SRC_DIR        - folder holding the upstream sources
#                          (src/, game.libretro/, LICENSE.md) plus the
#                          recipe-extracted dependency trees
#   KODI_SDK_INCLUDE_DIR - kodi-dev-kit include tree (provides kodi/ headers)
#   RCHEEVOS_SRC_DIR     - extracted rcheevos-9.2.0 tree (include/ + src/)

set(GAME_LIBRETRO_SOURCES ${ADDON_SRC_DIR}/src/client.cpp
                          ${ADDON_SRC_DIR}/src/GameInfoLoader.cpp
                          ${ADDON_SRC_DIR}/src/audio/AudioStream.cpp
                          ${ADDON_SRC_DIR}/src/audio/SingleFrameAudio.cpp
                          ${ADDON_SRC_DIR}/src/cheevos/Cheevos.cpp
                          ${ADDON_SRC_DIR}/src/cheevos/CheevosEnvironment.cpp
                          ${ADDON_SRC_DIR}/src/cheevos/CheevosFrontendBridge.cpp
                          ${ADDON_SRC_DIR}/src/input/ButtonMapper.cpp
                          ${ADDON_SRC_DIR}/src/input/ControllerLayout.cpp
                          ${ADDON_SRC_DIR}/src/input/ControllerTopology.cpp
                          ${ADDON_SRC_DIR}/src/input/DefaultControllerTranslator.cpp
                          ${ADDON_SRC_DIR}/src/input/DefaultKeyboardTranslator.cpp
                          ${ADDON_SRC_DIR}/src/input/InputManager.cpp
                          ${ADDON_SRC_DIR}/src/input/InputTranslator.cpp
                          ${ADDON_SRC_DIR}/src/input/LibretroDevice.cpp
                          ${ADDON_SRC_DIR}/src/input/LibretroDeviceInput.cpp
                          ${ADDON_SRC_DIR}/src/libretro/ClientBridge.cpp
                          ${ADDON_SRC_DIR}/src/libretro/FrontendBridge.cpp
                          ${ADDON_SRC_DIR}/src/libretro/LibretroDLL.cpp
                          ${ADDON_SRC_DIR}/src/libretro/LibretroEnvironment.cpp
                          ${ADDON_SRC_DIR}/src/libretro/LibretroResources.cpp
                          ${ADDON_SRC_DIR}/src/libretro/LibretroTranslator.cpp
                          ${ADDON_SRC_DIR}/src/libretro/MemoryMap.cpp
                          ${ADDON_SRC_DIR}/src/log/Log.cpp
                          ${ADDON_SRC_DIR}/src/log/LogAddon.cpp
                          ${ADDON_SRC_DIR}/src/log/LogConsole.cpp
                          ${ADDON_SRC_DIR}/src/settings/LanguageGenerator.cpp
                          ${ADDON_SRC_DIR}/src/settings/LibretroSetting.cpp
                          ${ADDON_SRC_DIR}/src/settings/LibretroSettings.cpp
                          ${ADDON_SRC_DIR}/src/settings/Settings.cpp
                          ${ADDON_SRC_DIR}/src/settings/SettingsGenerator.cpp
                          ${ADDON_SRC_DIR}/src/utils/Timer.cpp
                          ${ADDON_SRC_DIR}/src/video/VideoGeometry.cpp
                          ${ADDON_SRC_DIR}/src/video/VideoStream.cpp)

set(RCHEEVOS_SOURCES ${RCHEEVOS_SRC_DIR}/src/rcheevos/alloc.c
                     ${RCHEEVOS_SRC_DIR}/src/rcheevos/compat.c
                     ${RCHEEVOS_SRC_DIR}/src/rcheevos/condition.c
                     ${RCHEEVOS_SRC_DIR}/src/rcheevos/condset.c
                     ${RCHEEVOS_SRC_DIR}/src/rcheevos/consoleinfo.c
                     ${RCHEEVOS_SRC_DIR}/src/rcheevos/format.c
                     ${RCHEEVOS_SRC_DIR}/src/rcheevos/lboard.c
                     ${RCHEEVOS_SRC_DIR}/src/rcheevos/memref.c
                     ${RCHEEVOS_SRC_DIR}/src/rcheevos/operand.c
                     ${RCHEEVOS_SRC_DIR}/src/rcheevos/richpresence.c
                     ${RCHEEVOS_SRC_DIR}/src/rcheevos/runtime.c
                     ${RCHEEVOS_SRC_DIR}/src/rcheevos/runtime_progress.c
                     ${RCHEEVOS_SRC_DIR}/src/rcheevos/trigger.c
                     ${RCHEEVOS_SRC_DIR}/src/rcheevos/value.c
                     ${RCHEEVOS_SRC_DIR}/src/rhash/cdreader.c
                     ${RCHEEVOS_SRC_DIR}/src/rhash/hash.c
                     ${RCHEEVOS_SRC_DIR}/src/rhash/md5.c
                     ${RCHEEVOS_SRC_DIR}/src/rurl/url.c)

find_package(tinyxml CONFIG REQUIRED)

# Vendored rcheevos, mirroring the upstream depends/common/rcheevos build:
# same source list, RC_DISABLE_LUA, PIC static archive.
add_library(rcheevoslib STATIC ${RCHEEVOS_SOURCES})
target_include_directories(rcheevoslib PRIVATE ${RCHEEVOS_SRC_DIR}/include)
target_compile_definitions(rcheevoslib PRIVATE RC_DISABLE_LUA)
set_target_properties(rcheevoslib PROPERTIES POSITION_INDEPENDENT_CODE ON)

add_library(game.libretro MODULE ${GAME_LIBRETRO_SOURCES})
set_target_properties(game.libretro PROPERTIES PREFIX "")

target_include_directories(game.libretro PRIVATE
                           ${ADDON_SRC_DIR}/src
                           ${KODI_SDK_INCLUDE_DIR}
                           ${ADDON_SRC_DIR}/libretro-common-include
                           ${ADDON_SRC_DIR}/rcheevos-include)
target_compile_features(game.libretro PRIVATE cxx_std_17)
target_link_libraries(game.libretro PRIVATE tinyxml::tinyxml rcheevoslib)
