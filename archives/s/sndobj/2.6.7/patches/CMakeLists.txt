cmake_minimum_required(VERSION 3.15)
project(SndObj VERSION 2.6.7 LANGUAGES C CXX)

if(NOT SNDOBJ_SOURCE_ROOT OR NOT EXISTS "${SNDOBJ_SOURCE_ROOT}/src/SndObj.cpp")
  message(FATAL_ERROR "SNDOBJ_SOURCE_ROOT must name the verified 2.6.7 source tree")
endif()

# Upstream's SConstruct is Python-2-only. Use its same core source directories;
# the bundled FFTW 2 implementation is required by SndObj's public FFT API.
file(GLOB SNDOBJ_CPP CONFIGURE_DEPENDS "${SNDOBJ_SOURCE_ROOT}/src/*.cpp")
file(GLOB SNDOBJ_FFTW_C CONFIGURE_DEPENDS "${SNDOBJ_SOURCE_ROOT}/src/rfftw/*.c")
# These are alternative/unselected implementations, not part of SConstruct's
# normal source list. FFT_alt and IFFT_alt conflict with their selected peers.
list(REMOVE_ITEM SNDOBJ_CPP
  "${SNDOBJ_SOURCE_ROOT}/src/FFT_alt.cpp"
  "${SNDOBJ_SOURCE_ROOT}/src/IFFT_alt.cpp"
  "${SNDOBJ_SOURCE_ROOT}/src/SndASIO.cpp")
add_library(sndobj ${SNDOBJ_CPP} ${SNDOBJ_FFTW_C})
set_target_properties(sndobj PROPERTIES OUTPUT_NAME sndobj VERSION 2.6.7 SOVERSION 2)

find_package(Threads REQUIRED)
target_compile_definitions(sndobj PUBLIC NO_RTIO)
target_include_directories(sndobj
  PUBLIC
    "$<BUILD_INTERFACE:${SNDOBJ_SOURCE_ROOT}/src>"
    "$<BUILD_INTERFACE:${SNDOBJ_SOURCE_ROOT}/include>"
    "$<INSTALL_INTERFACE:include>"
  PRIVATE "${SNDOBJ_SOURCE_ROOT}/include/rfftw"
)
target_link_libraries(sndobj PRIVATE Threads::Threads)
if(UNIX)
  target_link_libraries(sndobj PRIVATE m)
endif()

install(TARGETS sndobj
  ARCHIVE DESTINATION lib
  LIBRARY DESTINATION lib
  RUNTIME DESTINATION bin)
install(DIRECTORY "${SNDOBJ_SOURCE_ROOT}/src/" DESTINATION include/SndObj
  FILES_MATCHING PATTERN "*.h")
install(DIRECTORY "${SNDOBJ_SOURCE_ROOT}/include/rfftw/" DESTINATION include/rfftw
  FILES_MATCHING PATTERN "*.h")
