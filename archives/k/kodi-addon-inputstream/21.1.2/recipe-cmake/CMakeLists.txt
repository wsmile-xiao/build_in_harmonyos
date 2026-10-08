# Standalone build entry for the unmodified upstream sources of
# inputstream.adaptive 21.1.2-Omega on OHOS (aarch64-linux-ohos).
#
# The upstream CMakeLists.txt resolves its build through modules shipped with
# the kodi-addon-dev distribution (find_package(Kodi) + build_addon() from
# AddonHelpers.cmake, FindBento4.cmake, FindPugixml.cmake), which expects a
# Kodi SDK installation. This entry builds the same unmodified sources with
# the recipe-provided Kodi SDK include tree, replicating the upstream flow
# parts that matter:
#   - module target inputstream.adaptive with PREFIX "" (build_addon), the
#     full upstream ADP_SOURCES list, upstream compile definitions
#     (__STDC_FORMAT_MACROS / UNICODE / _UNICODE), linking the in-tree
#     bundled libs mpegts + webm_parser and conan bento4 + pugixml
#   - module target ssd_wv: the posix branch of upstream
#     wvdecrypter/CMakeLists.txt verbatim (INPUTSTREAM_SSD_BUILD +
#     WIDEVINECDMFILENAME="libwidevinecdm.so", cdm/ include, links bento4 +
#     CMAKE_DL_LIBS; source set and definitions copied 1:1)
#   - bundled static libs mpegts / webm_parser built from the unmodified
#     upstream in-tree CMakeLists (add_subdirectory); both already declare
#     POSITION_INDEPENDENT_CODE / include dirs themselves
#   - optional upstream test build (INPUTSTREAM_TESTS=ON): the src/test
#     suite (51 TEST_F cases over DASH/HLS/Smooth tree parsers + utils)
#     against upstream's own KodiStubs.h stub header, replicating
#     src/test/CMakeLists.txt with conan-provided gtest/pugixml targets.
#     KodiStubs.h is self-contained (no kodi/ SDK headers), so the tests
#     need no real Kodi SDK and run fully offline (curl is stubbed).
# Upstream sources are consumed unmodified from ADDON_SRC_DIR.
#
# Recipe inputs, set through CMakeToolchain variables in conanfile.py:
#   ADDON_SRC_DIR        - folder holding the upstream sources
#   KODI_SDK_INCLUDE_DIR - kodi-dev-kit include tree (provides kodi/ headers)
#   INPUTSTREAM_TESTS    - ON to also build the upstream src/test suite
cmake_minimum_required(VERSION 3.15)
project(inputstream.adaptive LANGUAGES CXX C)

find_package(pugixml CONFIG REQUIRED)
find_package(Threads REQUIRED)

# Upstream top-level CMakeLists builds the bundled static libs with
# POSITION_INDEPENDENT_CODE (they are linked into the shared add-on module).
set(CMAKE_POSITION_INDEPENDENT_CODE ON)

# ── bundled bento4 fork (upstream ENABLE_INTERNAL_BENTO4 flow) ──
# Built from the fork's own unmodified CMakeLists (extracted in source(),
# BENTO4_SRC): static lib target "ap4", -DBUILD_APPS=OFF like the upstream
# externalproject flags (depends/common/bento4/flags.txt). PIC comes from
# CMAKE_POSITION_INDEPENDENT_CODE above (upstream passes -fPIC).
# Cache-level FORCE: the fork's cmake_minimum_required(3.10) keeps CMP0077
# OLD, whose option() would wipe a plain set() variable and re-create the
# cache entry with its default ON.
set(BUILD_APPS OFF CACHE BOOL "" FORCE)
add_subdirectory("${BENTO4_SRC}" bento4 EXCLUDE_FROM_ALL)
# Public headers staged in source() under <BENTO4_INCLUDE_STAGING>/bento4/
# (the installed layout the upstream code #includes: <bento4/Ap4.h>).
set(BENTO4_STAGED_INCLUDE "${BENTO4_INCLUDE_STAGING}")

# ── bundled static libraries (upstream in-tree CMakeLists, unmodified) ──
add_subdirectory("${ADDON_SRC_DIR}/lib/mpegts" mpegts EXCLUDE_FROM_ALL)
add_subdirectory("${ADDON_SRC_DIR}/lib/webm_parser" webm_parser EXCLUDE_FROM_ALL)

# ── the add-on module: upstream ADP_SOURCES, unmodified ──
set(ADP_SOURCES
    ${ADDON_SRC_DIR}/src/AdaptiveByteStream.cpp
    ${ADDON_SRC_DIR}/src/main.cpp
    ${ADDON_SRC_DIR}/src/codechandler/CodecHandler.cpp
    ${ADDON_SRC_DIR}/src/codechandler/AV1CodecHandler.cpp
    ${ADDON_SRC_DIR}/src/codechandler/AVCCodecHandler.cpp
    ${ADDON_SRC_DIR}/src/codechandler/HEVCCodecHandler.cpp
    ${ADDON_SRC_DIR}/src/codechandler/MPEGCodecHandler.cpp
    ${ADDON_SRC_DIR}/src/codechandler/TTMLCodecHandler.cpp
    ${ADDON_SRC_DIR}/src/codechandler/VP9CodecHandler.cpp
    ${ADDON_SRC_DIR}/src/codechandler/WebVTTCodecHandler.cpp
    ${ADDON_SRC_DIR}/src/codechandler/ttml/TTML.cpp
    ${ADDON_SRC_DIR}/src/common/AdaptationSet.cpp
    ${ADDON_SRC_DIR}/src/common/AdaptiveCencSampleDecrypter.cpp
    ${ADDON_SRC_DIR}/src/common/AdaptiveStream.cpp
    ${ADDON_SRC_DIR}/src/common/AdaptiveTree.cpp
    ${ADDON_SRC_DIR}/src/common/AdaptiveTreeFactory.cpp
    ${ADDON_SRC_DIR}/src/common/AdaptiveUtils.cpp
    ${ADDON_SRC_DIR}/src/common/Chooser.cpp
    ${ADDON_SRC_DIR}/src/common/ChooserAskQuality.cpp
    ${ADDON_SRC_DIR}/src/common/ChooserDefault.cpp
    ${ADDON_SRC_DIR}/src/common/ChooserFixedRes.cpp
    ${ADDON_SRC_DIR}/src/common/ChooserManualOSD.cpp
    ${ADDON_SRC_DIR}/src/common/ChooserTest.cpp
    ${ADDON_SRC_DIR}/src/common/CommonAttribs.cpp
    ${ADDON_SRC_DIR}/src/common/CommonSegAttribs.cpp
    ${ADDON_SRC_DIR}/src/common/Period.cpp
    ${ADDON_SRC_DIR}/src/common/Representation.cpp
    ${ADDON_SRC_DIR}/src/common/ReprSelector.cpp
    ${ADDON_SRC_DIR}/src/common/Segment.cpp
    ${ADDON_SRC_DIR}/src/common/SegmentList.cpp
    ${ADDON_SRC_DIR}/src/common/SegTemplate.cpp
    ${ADDON_SRC_DIR}/src/parser/CodecParser.cpp
    ${ADDON_SRC_DIR}/src/parser/DASHTree.cpp
    ${ADDON_SRC_DIR}/src/parser/HLSTree.cpp
    ${ADDON_SRC_DIR}/src/parser/SmoothTree.cpp
    ${ADDON_SRC_DIR}/src/parser/PRProtectionParser.cpp
    ${ADDON_SRC_DIR}/src/samplereader/ADTSSampleReader.cpp
    ${ADDON_SRC_DIR}/src/samplereader/FragmentedSampleReader.cpp
    ${ADDON_SRC_DIR}/src/samplereader/SubtitleSampleReader.cpp
    ${ADDON_SRC_DIR}/src/samplereader/TSSampleReader.cpp
    ${ADDON_SRC_DIR}/src/samplereader/WebmSampleReader.cpp
    ${ADDON_SRC_DIR}/src/utils/Base64Utils.cpp
    ${ADDON_SRC_DIR}/src/utils/CharArrayParser.cpp
    ${ADDON_SRC_DIR}/src/utils/CurlUtils.cpp
    ${ADDON_SRC_DIR}/src/utils/DigestMD5Utils.cpp
    ${ADDON_SRC_DIR}/src/utils/FileUtils.cpp
    ${ADDON_SRC_DIR}/src/utils/MemUtils.cpp
    ${ADDON_SRC_DIR}/src/utils/PropertiesUtils.cpp
    ${ADDON_SRC_DIR}/src/utils/StringUtils.cpp
    ${ADDON_SRC_DIR}/src/utils/SettingsUtils.cpp
    ${ADDON_SRC_DIR}/src/utils/UrlUtils.cpp
    ${ADDON_SRC_DIR}/src/utils/Utils.cpp
    ${ADDON_SRC_DIR}/src/utils/XMLUtils.cpp
    ${ADDON_SRC_DIR}/src/KodiHost.cpp
    ${ADDON_SRC_DIR}/src/oscompat.cpp
    ${ADDON_SRC_DIR}/src/Session.cpp
    ${ADDON_SRC_DIR}/src/Stream.cpp
    ${ADDON_SRC_DIR}/src/TSReader.cpp
    ${ADDON_SRC_DIR}/src/aes_decrypter.cpp
    ${ADDON_SRC_DIR}/src/ADTSReader.cpp
    ${ADDON_SRC_DIR}/src/WebmReader.cpp
    )

add_library(inputstream.adaptive MODULE ${ADP_SOURCES})
set_target_properties(inputstream.adaptive PROPERTIES PREFIX "")
target_include_directories(inputstream.adaptive PRIVATE
                           "${ADDON_SRC_DIR}/src"
                           "${ADDON_SRC_DIR}/lib/webm_parser/include"
                           "${BENTO4_STAGED_INCLUDE}"
                           "${KODI_SDK_INCLUDE_DIR}")
# Upstream top-level CMakeLists: add_definitions(-D__STDC_FORMAT_MACROS
# -DUNICODE -D_UNICODE) on the non-WIN32 branch.
target_compile_definitions(inputstream.adaptive PRIVATE
                           __STDC_FORMAT_MACROS UNICODE _UNICODE)
target_compile_features(inputstream.adaptive PRIVATE cxx_std_17)
# Explicit relative DT_SONAME (kodi-inputstream-rtmp/21.1.2 CI precedent;
# dlopen()ed by the host, so the soname matches the file name).
target_link_options(inputstream.adaptive PRIVATE
                    "-Wl,-soname,inputstream.adaptive.so")
target_link_libraries(inputstream.adaptive PRIVATE
                      ap4
                      pugixml::pugixml
                      mpegts
                      webm_parser)

# ── the Widevine SSD helper module: wvdecrypter posix branch ──
# Source set / definitions / include dirs / link list copied 1:1 from the
# non-android non-win non-darwin branch of upstream
# wvdecrypter/CMakeLists.txt.
set(SSD_SRC "${ADDON_SRC_DIR}/wvdecrypter")
set(SSD_SOURCES
    ${SSD_SRC}/Helper.cpp
    ${SSD_SRC}/wvdecrypter.cpp
    ${SSD_SRC}/jsmn.c
    ${ADDON_SRC_DIR}/src/utils/Utils.cpp
    ${ADDON_SRC_DIR}/src/utils/StringUtils.cpp
    ${ADDON_SRC_DIR}/src/utils/Base64Utils.cpp
    ${ADDON_SRC_DIR}/src/utils/DigestMD5Utils.cpp
    ${SSD_SRC}/cdm/base/native_library.cc
    ${SSD_SRC}/cdm/base/native_library_posix.cc
    ${SSD_SRC}/cdm/media/cdm/cdm_adapter.cc
    ${SSD_SRC}/cdm/media/cdm/cdm_type_conversion.cc
    )

add_library(ssd_wv MODULE ${SSD_SOURCES})
set_target_properties(ssd_wv PROPERTIES PREFIX "")
target_include_directories(ssd_wv PRIVATE
                           "${SSD_SRC}"
                           "${SSD_SRC}/cdm"
                           "${ADDON_SRC_DIR}/src"
                           "${BENTO4_STAGED_INCLUDE}"
                           "${KODI_SDK_INCLUDE_DIR}")
target_compile_definitions(ssd_wv PRIVATE
                           INPUTSTREAM_SSD_BUILD
                           WIDEVINECDMFILENAME="libwidevinecdm.so")
target_link_options(ssd_wv PRIVATE "-Wl,-soname,ssd_wv.so")
target_link_libraries(ssd_wv PRIVATE ap4 ${CMAKE_DL_LIBS})

# ── optional upstream test build (R51) ──
option(INPUTSTREAM_TESTS "Also build the upstream src/test suite" OFF)
if(INPUTSTREAM_TESTS)
  find_package(gtest CONFIG REQUIRED)

  set(TEST_SOURCES
      ${ADDON_SRC_DIR}/src/test/TestMain.cpp
      ${ADDON_SRC_DIR}/src/test/TestDASHTree.cpp
      ${ADDON_SRC_DIR}/src/test/TestHLSTree.cpp
      ${ADDON_SRC_DIR}/src/test/TestSmoothTree.cpp
      ${ADDON_SRC_DIR}/src/test/TestHelper.cpp
      ${ADDON_SRC_DIR}/src/test/TestUtils.cpp
      ${ADDON_SRC_DIR}/src/parser/DASHTree.cpp
      ${ADDON_SRC_DIR}/src/parser/HLSTree.cpp
      ${ADDON_SRC_DIR}/src/parser/SmoothTree.cpp
      ${ADDON_SRC_DIR}/src/parser/PRProtectionParser.cpp
      ${ADDON_SRC_DIR}/src/common/AdaptationSet.cpp
      ${ADDON_SRC_DIR}/src/common/AdaptiveStream.cpp
      ${ADDON_SRC_DIR}/src/common/AdaptiveTree.cpp
      ${ADDON_SRC_DIR}/src/common/AdaptiveTreeFactory.cpp
      ${ADDON_SRC_DIR}/src/common/AdaptiveUtils.cpp
      ${ADDON_SRC_DIR}/src/common/Chooser.cpp
      ${ADDON_SRC_DIR}/src/common/ChooserAskQuality.cpp
      ${ADDON_SRC_DIR}/src/common/ChooserDefault.cpp
      ${ADDON_SRC_DIR}/src/common/ChooserFixedRes.cpp
      ${ADDON_SRC_DIR}/src/common/ChooserManualOSD.cpp
      ${ADDON_SRC_DIR}/src/common/ChooserTest.cpp
      ${ADDON_SRC_DIR}/src/common/CommonAttribs.cpp
      ${ADDON_SRC_DIR}/src/common/CommonSegAttribs.cpp
      ${ADDON_SRC_DIR}/src/common/Period.cpp
      ${ADDON_SRC_DIR}/src/common/Representation.cpp
      ${ADDON_SRC_DIR}/src/common/ReprSelector.cpp
      ${ADDON_SRC_DIR}/src/common/Segment.cpp
      ${ADDON_SRC_DIR}/src/common/SegmentList.cpp
      ${ADDON_SRC_DIR}/src/common/SegTemplate.cpp
      ${ADDON_SRC_DIR}/src/oscompat.cpp
      ${ADDON_SRC_DIR}/src/utils/Base64Utils.cpp
      ${ADDON_SRC_DIR}/src/utils/CharArrayParser.cpp
      ${ADDON_SRC_DIR}/src/utils/CurlUtils.cpp
      ${ADDON_SRC_DIR}/src/utils/FileUtils.cpp
      ${ADDON_SRC_DIR}/src/utils/PropertiesUtils.cpp
      ${ADDON_SRC_DIR}/src/utils/SettingsUtils.cpp
      ${ADDON_SRC_DIR}/src/utils/StringUtils.cpp
      ${ADDON_SRC_DIR}/src/utils/UrlUtils.cpp
      ${ADDON_SRC_DIR}/src/utils/Utils.cpp
      ${ADDON_SRC_DIR}/src/utils/XMLUtils.cpp
      )

  add_executable(inputstream.adaptive_test ${TEST_SOURCES})
  # Upstream tests run inside the kodi build_addon environment (global
  # INCLUDES carry the SDK headers and the Bento4 include dir; e.g. the
  # reused src/utils/log.h includes kodi/tools/StringUtils.h and
  # src/Iaes_decrypter.h includes <bento4/Ap4Types.h>).
  target_include_directories(inputstream.adaptive_test PRIVATE
                             "${ADDON_SRC_DIR}/src/test"
                             "${ADDON_SRC_DIR}/src"
                             "${BENTO4_STAGED_INCLUDE}"
                             "${KODI_SDK_INCLUDE_DIR}")
  target_compile_definitions(inputstream.adaptive_test PRIVATE
                             INPUTSTREAM_TEST_BUILD)
  target_compile_features(inputstream.adaptive_test PRIVATE cxx_std_17)
  target_link_libraries(inputstream.adaptive_test PRIVATE
                        ap4
                        pugixml::pugixml
                        gtest::gtest
                        Threads::Threads
                        ${CMAKE_DL_LIBS})

  # Upstream src/test/CMakeLists.txt registers the same command with
  # TEST_DATA_DIR=src/test/manifests; TestMain setenv("DATADIR", argv[1]).
  set(TEST_DATA_DIR "${ADDON_SRC_DIR}/src/test/manifests")
  enable_testing()
  add_test(NAME manifest_tests
           COMMAND inputstream.adaptive_test "${TEST_DATA_DIR}")
endif()
