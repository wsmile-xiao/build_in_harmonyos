cmake_minimum_required(VERSION 3.15)
project(test_cubicsdr_core CXX)

find_package(cubicsdr-core CONFIG REQUIRED)
# cubicsdr-core public headers include liquid/liquid.h (liquid-dsp is a
# public dependency); pull its target in so the include path propagates.
find_package(liquid CONFIG REQUIRED)
find_package(SoapySDR CONFIG REQUIRED)

# Locate the mirrored upstream src/ tree inside the package.
get_target_property(CUBICSDR_CORE_INCLUDE_DIR cubicsdr-core::cubicsdr-core
                    INTERFACE_INCLUDE_DIRECTORIES)

add_executable(test_cubicsdr_core test_package.cpp)
# cubicsdr-core upstream headers use flat includes within the src tree
# (e.g. Modem.h does #include "IOThread.h"); expose the mirrored src
# tree roots so consumer compilation matches upstream layout.
target_include_directories(test_cubicsdr_core PRIVATE
    ${CUBICSDR_CORE_INCLUDE_DIR}/src
    ${CUBICSDR_CORE_INCLUDE_DIR}/src/util
    ${CUBICSDR_CORE_INCLUDE_DIR}/src/modules/modem
    ${CUBICSDR_CORE_INCLUDE_DIR}/src/modules/modem/analog
    ${CUBICSDR_CORE_INCLUDE_DIR}/src/modules/modem/digital
    ${CUBICSDR_CORE_INCLUDE_DIR}/src/audio
    ${CUBICSDR_CORE_INCLUDE_DIR}/src/demod
    ${CUBICSDR_CORE_INCLUDE_DIR}/src/sdr
    ${CUBICSDR_CORE_INCLUDE_DIR}/external/rtaudio
    ${CUBICSDR_CORE_INCLUDE_DIR}/external/tinyxml
)
target_link_libraries(test_cubicsdr_core cubicsdr-core::cubicsdr-core)
target_link_libraries(test_cubicsdr_core liquid::liquid-static)
target_link_libraries(test_cubicsdr_core SoapySDR::SoapySDR)
if(CMAKE_SYSTEM_NAME STREQUAL "HarmonyOS" OR CMAKE_SYSTEM_NAME STREQUAL "Linux")
    target_link_libraries(test_cubicsdr_core m pthread dl)
endif()
target_compile_features(test_cubicsdr_core PRIVATE cxx_std_17)

enable_testing()
add_test(NAME test_cubicsdr_core COMMAND test_cubicsdr_core)
