cmake_minimum_required(VERSION 3.15)
project(test_package CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# The installed mapnikTargets.cmake re-exports the upstream ICU component
# target names (ICU::uc/ICU::i18n/ICU::data). The conan icu4c package
# declares no CMake config properties (no icu4cConfig.cmake is generated
# for consumers), so bridge the targets manually: headers and libraries
# are resolved through the paths conan propagates (CMAKE_LIBRARY_PATH /
# CMAKE_INCLUDE_PATH in conan_toolchain.cmake).
if(NOT TARGET ICU::uc)
    find_path(ICU4C_INCLUDE_DIR unicode/unistr.h REQUIRED)
    find_library(ICU4C_LIB_uc NAMES icuuc REQUIRED)
    find_library(ICU4C_LIB_i18n NAMES icui18n REQUIRED)
    find_library(ICU4C_LIB_data NAMES icudata REQUIRED)
    add_library(ICU::uc INTERFACE IMPORTED)
    target_include_directories(ICU::uc INTERFACE "${ICU4C_INCLUDE_DIR}")
    target_link_libraries(ICU::uc INTERFACE
        "${ICU4C_LIB_uc}" "${ICU4C_LIB_i18n}" "${ICU4C_LIB_data}")
endif()

find_package(mapnik CONFIG REQUIRED)

# The conan boost package's CMakeDeps config leaves the Boost::headers
# component's INTERFACE_INCLUDE_DIRECTORIES empty (empty include dir list in
# the generated data file), so the upstream mapnik::core closure does not
# propagate the boost headers to consumers. Fix the imported target here.
if(TARGET Boost::headers)
    find_path(BOOST_INCLUDE_DIR boost/version.hpp REQUIRED)
    set_property(TARGET Boost::headers APPEND PROPERTY
        INTERFACE_INCLUDE_DIRECTORIES "${BOOST_INCLUDE_DIR}")
endif()

# mapnik's public headers include <hb.h> directly (the conan harfbuzz
# package exposes its headers via include/harfbuzz, patched include style);
# attach that include dir to the harfbuzz target for consumers.
if(TARGET harfbuzz::harfbuzz)
    find_path(HB_INCLUDE_DIR hb.h REQUIRED)
    set_property(TARGET harfbuzz::harfbuzz APPEND PROPERTY
        INTERFACE_INCLUDE_DIRECTORIES "${HB_INCLUDE_DIR}")
endif()

add_executable(test_package src/test_package.cpp)
# mapnik::mapnik (SHARED IMPORTED) does not re-export its interface; the
# link closure lives on mapnik::core (Boost::headers, ICU targets, freetype,
# harfbuzz, ...) and the agg/json/wkt helper libraries.
target_link_libraries(test_package PRIVATE mapnik::mapnik mapnik::core mapnik::agg mapnik::json mapnik::wkt)
