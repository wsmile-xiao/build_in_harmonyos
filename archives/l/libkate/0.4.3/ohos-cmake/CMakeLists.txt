cmake_minimum_required(VERSION 3.15)
project(libkate LANGUAGES C)

find_package(libogg CONFIG REQUIRED)
find_package(libpng CONFIG REQUIRED)

set(KATE_SOURCES
    "${KATE_SOURCE_DIR}/src/kate.c"
    "${KATE_SOURCE_DIR}/src/kate_info.c"
    "${KATE_SOURCE_DIR}/src/kate_comment.c"
    "${KATE_SOURCE_DIR}/src/kate_granule.c"
    "${KATE_SOURCE_DIR}/src/kate_event.c"
    "${KATE_SOURCE_DIR}/src/kate_motion.c"
    "${KATE_SOURCE_DIR}/src/kate_text.c"
    "${KATE_SOURCE_DIR}/src/kate_tracker.c"
    "${KATE_SOURCE_DIR}/src/kate_fp.c"
    "${KATE_SOURCE_DIR}/src/kate_font.c"
    "${KATE_SOURCE_DIR}/src/kate_encode_state.c"
    "${KATE_SOURCE_DIR}/src/kate_encode.c"
    "${KATE_SOURCE_DIR}/src/kate_decode_state.c"
    "${KATE_SOURCE_DIR}/src/kate_decode.c"
    "${KATE_SOURCE_DIR}/src/kate_packet.c"
    "${KATE_SOURCE_DIR}/src/kate_bitwise.c"
    "${KATE_SOURCE_DIR}/src/kate_rle.c"
    "${KATE_SOURCE_DIR}/src/kate_meta.c"
    "${KATE_SOURCE_DIR}/src/kate_high.c"
)

configure_file(
    "${CMAKE_CURRENT_SOURCE_DIR}/config.h.in"
    "${CMAKE_CURRENT_BINARY_DIR}/include/config.h"
)

add_library(kate ${KATE_SOURCES})
target_compile_definitions(kate PRIVATE HAVE_CONFIG_H=1)
target_include_directories(
    kate
    PUBLIC
        "$<BUILD_INTERFACE:${KATE_SOURCE_DIR}/include>"
        "$<INSTALL_INTERFACE:include>"
    PRIVATE
        "${KATE_SOURCE_DIR}/src"
        "${CMAKE_CURRENT_BINARY_DIR}/include"
)
target_link_libraries(kate PRIVATE libpng::libpng)
set_target_properties(kate PROPERTIES VERSION 4.2.3 SOVERSION 1)

add_library(oggkate "${KATE_SOURCE_DIR}/src/kate_ogg.c")
target_compile_definitions(oggkate PRIVATE HAVE_CONFIG_H=1)
target_include_directories(
    oggkate
    PUBLIC
        "$<BUILD_INTERFACE:${KATE_SOURCE_DIR}/include>"
        "$<INSTALL_INTERFACE:include>"
    PRIVATE
        "${KATE_SOURCE_DIR}/src"
        "${CMAKE_CURRENT_BINARY_DIR}/include"
)
target_link_libraries(oggkate PRIVATE kate libogg::libogg)
set_target_properties(oggkate PROPERTIES VERSION 3.4.2 SOVERSION 1)

install(
    TARGETS kate oggkate
    ARCHIVE DESTINATION lib
    LIBRARY DESTINATION lib
    RUNTIME DESTINATION bin
)
install(
    FILES
        "${KATE_SOURCE_DIR}/include/kate/kate.h"
        "${KATE_SOURCE_DIR}/include/kate/kate_config.h"
        "${KATE_SOURCE_DIR}/include/kate/oggkate.h"
    DESTINATION include/kate
)
