# Standalone build entry for the unmodified upstream sources of
# screensaver.asteroids 21.0.2-Omega on OHOS (GLES render path).
#
# The upstream CMakeLists.txt needs find_package(Kodi) + build_addon()
# from the kodi-addon-dev distribution (not packaged on the ohpcd registry).
# This entry builds the same sources with the recipe-provided Kodi SDK
# include tree, replicating the parts of the upstream flow that matter:
#   - module target named screensaver.asteroids with PREFIX "" (build_addon)
#   - APP_RENDER_SYSTEM=gles: HAS_GLES=3 (upstream FindOpenGLES sets
#     -DHAS_GLES=3 when GLES3 headers are found) and system GLESv3/EGL
#   - POSITION_INDEPENDENT_CODE (build_addon sets it for the shared module)
# Upstream sources are consumed unmodified from ../src.
cmake_minimum_required(VERSION 3.5)
project(screensaver.asteroids CXX)

# Recipe inputs, set through CMakeToolchain variables in conanfile.py:
#   ADDON_SRC_DIR        - folder holding the upstream sources (src/, LICENSE.md)
#   KODI_SDK_INCLUDE_DIR - kodi-dev-kit include tree (provides kodi/ headers)

set(ASTEROIDS_SOURCES ${ADDON_SRC_DIR}/src/asteroid.cpp
                      ${ADDON_SRC_DIR}/src/Asteroids.cpp
                      ${ADDON_SRC_DIR}/src/bullet.cpp
                      ${ADDON_SRC_DIR}/src/main.cpp
                      ${ADDON_SRC_DIR}/src/ship.cpp)

find_package(glm CONFIG REQUIRED)

add_library(${PROJECT_NAME} MODULE ${ASTEROIDS_SOURCES})
set_target_properties(${PROJECT_NAME} PROPERTIES PREFIX "")

target_include_directories(${PROJECT_NAME} PRIVATE
                           ${ADDON_SRC_DIR}/src
                           ${KODI_SDK_INCLUDE_DIR})
target_compile_features(${PROJECT_NAME} PRIVATE cxx_std_17)
# HAS_GLES=3 selects the GLES3 branch of the SDK's kodi/gui/gl/GL.h and the
# resources/shaders/GLES shader set (GL_TYPE_STRING "GLES"). The addon's
# src/main.h keeps <d3d11.h> behind "#ifndef WIN32", so no further platform
# define is needed on OHOS.
target_compile_definitions(${PROJECT_NAME} PRIVATE HAS_GLES=3)
target_link_libraries(${PROJECT_NAME} PRIVATE glm::glm GLESv3 EGL)
