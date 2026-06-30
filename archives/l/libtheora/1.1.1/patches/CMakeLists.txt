# CMakeLists.txt for libtheora 1.1.1
# Created for OpenHarmony cross-compilation

cmake_minimum_required(VERSION 3.10)
project(theora VERSION 1.1.1 LANGUAGES C)

# Set default build type
if(NOT CMAKE_BUILD_TYPE)
    set(CMAKE_BUILD_TYPE Release)
endif()

# Find libogg dependency
find_package(PkgConfig REQUIRED)
pkg_check_modules(OGG REQUIRED ogg)

# Include directories
include_directories(
    ${CMAKE_CURRENT_SOURCE_DIR}/include
    ${OGG_INCLUDE_DIRS}
)

# Source files for theora library
set(THEORA_DEC_SOURCES
    lib/analyze.c
    lib/apiwrapper.c
    lib/bitpack.c
    lib/decapiwrapper.c
    lib/decinfo.c
    lib/decode.c
    lib/dequant.c
    lib/fragment.c
    lib/huffdec.c
    lib/idct.c
    lib/info.c
    lib/internal.c
    lib/mathops.c
    lib/quant.c
    lib/state.c
)

set(THEORA_ENC_SOURCES
    lib/analyze.c
    lib/apiwrapper.c
    lib/bitpack.c
    lib/encapiwrapper.c
    lib/encfrag.c
    lib/encinfo.c
    lib/encode.c
    lib/enquant.c
    lib/fdct.c
    lib/huffenc.c
    lib/mathops.c
    lib/quant.c
    lib/rate.c
    lib/state.c
    lib/tokenize.c
)

# Build static libraries
add_library(theoradec STATIC ${THEORA_DEC_SOURCES})
target_link_libraries(theoradec ${OGG_LIBRARIES})
target_compile_options(theoradec PRIVATE -O2 -fPIC)

add_library(theoraenc STATIC ${THEORA_ENC_SOURCES})
target_link_libraries(theoraenc ${OGG_LIBRARIES})
target_compile_options(theoraenc PRIVATE -O2 -fPIC)

# Combined theora library (includes both dec and enc)
add_library(theora STATIC ${THEORA_DEC_SOURCES} ${THEORA_ENC_SOURCES})
target_link_libraries(theora ${OGG_LIBRARIES})
target_compile_options(theora PRIVATE -O2 -fPIC)

# Install targets
install(TARGETS theora theoradec theoraenc
    ARCHIVE DESTINATION lib
    LIBRARY DESTINATION lib
)

# Install headers
install(DIRECTORY include/theora/
    DESTINATION include/theora
    FILES_MATCHING PATTERN "*.h"
)

# Generate pkg-config files
configure_file(theora.pc.in theora.pc @ONLY)
configure_file(theoradec.pc.in theoradec.pc @ONLY)
configure_file(theoraenc.pc.in theoraenc.pc @ONLY)

install(FILES
    ${CMAKE_CURRENT_BINARY_DIR}/theora.pc
    ${CMAKE_CURRENT_BINARY_DIR}/theoradec.pc
    ${CMAKE_CURRENT_BINARY_DIR}/theoraenc.pc
    DESTINATION lib/pkgconfig
)