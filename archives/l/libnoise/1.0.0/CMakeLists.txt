cmake_minimum_required(VERSION 3.15)
project(libnoise LANGUAGES CXX)

# Build description for the upstream libnoise 1.0.0 sources.  The upstream
# release drives its hand-written Makefiles through libtool, which is not
# available in the OHOS build environment; this file compiles the identical
# 35-source translation-unit list declared in noise/src/Sources without
# modifying any upstream file.

set(LIBNOISE_SOURCES
    noise/src/latlon.cpp
    noise/src/noisegen.cpp
    noise/src/model/cylinder.cpp
    noise/src/model/line.cpp
    noise/src/model/plane.cpp
    noise/src/model/sphere.cpp
    noise/src/module/abs.cpp
    noise/src/module/add.cpp
    noise/src/module/billow.cpp
    noise/src/module/blend.cpp
    noise/src/module/cache.cpp
    noise/src/module/checkerboard.cpp
    noise/src/module/clamp.cpp
    noise/src/module/const.cpp
    noise/src/module/curve.cpp
    noise/src/module/cylinders.cpp
    noise/src/module/displace.cpp
    noise/src/module/exponent.cpp
    noise/src/module/invert.cpp
    noise/src/module/max.cpp
    noise/src/module/min.cpp
    noise/src/module/modulebase.cpp
    noise/src/module/multiply.cpp
    noise/src/module/perlin.cpp
    noise/src/module/power.cpp
    noise/src/module/ridgedmulti.cpp
    noise/src/module/rotatepoint.cpp
    noise/src/module/scalebias.cpp
    noise/src/module/scalepoint.cpp
    noise/src/module/select.cpp
    noise/src/module/spheres.cpp
    noise/src/module/terrace.cpp
    noise/src/module/translatepoint.cpp
    noise/src/module/turbulence.cpp
    noise/src/module/voronoi.cpp
)

add_library(noise ${LIBNOISE_SOURCES})
target_include_directories(noise
    PUBLIC
        $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/noise/src>
        $<INSTALL_INTERFACE:include>)
# Upstream soname chain: libnoise.so.0.3 with SONAME libnoise.so.0.
set_target_properties(noise PROPERTIES
    VERSION 0.3
    SOVERSION 0)

install(TARGETS noise
    RUNTIME DESTINATION bin
    LIBRARY DESTINATION lib
    ARCHIVE DESTINATION lib)
# Mirror the upstream install layout: consumers include <noise/noise.h> with
# the module/ and model/ subtrees preserved under include/noise/.  The MSVC
# resource shim noise/src/win32/ (resource.h et al) is not part of the public
# API and upstream's include/Makefile does not install it; exclude it too.
install(DIRECTORY noise/src/
    DESTINATION include/noise
    FILES_MATCHING
    PATTERN "*.h"
    REGEX "/win32$" EXCLUDE)
