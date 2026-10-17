cmake_minimum_required(VERSION 3.15)
project(fathom VERSION 1.0 LANGUAGES C)

# Fathom 1.0 ships no library build system upstream (src/apps/Makefile only
# builds the CLI). This injected file builds the probing library the way
# upstream builds it: tbprobe.c is a single translation unit that
# #includes tbcore.c, compiled as C99 with GNU extensions and with
# TB_NO_THREADS / TB_NO_HW_POP_COUNT — the same defines upstream's
# src/apps/Makefile passes.
add_library(fathom STATIC src/tbprobe.c)

set_target_properties(fathom PROPERTIES
    C_STANDARD 99
    C_STANDARD_REQUIRED ON
    C_EXTENSIONS ON
)

target_compile_definitions(fathom PRIVATE
    TB_NO_THREADS
    TB_NO_HW_POP_COUNT
)

target_include_directories(fathom PUBLIC
    $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/src>
    $<INSTALL_INTERFACE:include>
)

install(TARGETS fathom
    ARCHIVE DESTINATION lib
)
install(FILES src/tbprobe.h src/tbconfig.h
    DESTINATION include
)
