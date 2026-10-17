cmake_minimum_required(VERSION 3.15)
project(alac VERSION 0.0.7 LANGUAGES C CXX)

# ALAC codec library
set(ALAC_SOURCES
    codec/ALACBitUtilities.c
    codec/ALACDecoder.cpp
    codec/ALACEncoder.cpp
    codec/EndianPortable.c
    codec/ag_dec.c
    codec/ag_enc.c
    codec/dp_dec.c
    codec/dp_enc.c
    codec/matrix_dec.c
    codec/matrix_enc.c
)

set(ALAC_HEADERS
    codec/ALACAudioTypes.h
    codec/ALACBitUtilities.h
    codec/ALACDecoder.h
    codec/ALACEncoder.h
    codec/EndianPortable.h
    codec/aglib.h
    codec/dplib.h
    codec/matrixlib.h
)

# Build static library
add_library(ALAC STATIC ${ALAC_SOURCES})

# Set C++ standard
target_compile_features(ALAC PUBLIC cxx_std_98)

# Include directories
target_include_directories(ALAC PUBLIC
    $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/codec>
    $<INSTALL_INTERFACE:include>
)

# Suppress warnings for old-style code
target_compile_options(ALAC PRIVATE
    $<$<COMPILE_LANGUAGE:C>:-w>
    $<$<COMPILE_LANGUAGE:CXX>:-w>
)

# Install
install(TARGETS ALAC
    ARCHIVE DESTINATION lib
)
install(FILES ${ALAC_HEADERS}
    DESTINATION include
)