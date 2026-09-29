# fuzzrun — 在目标设备上真实执行 libwebp 1.6.0 上游 tests/fuzzer/ 的 12 个 fuzz 目标。
#
# 机制(上游测试源码零改动):
#   1. 以 add_subdirectory 静态构建上游 libwebp(webp/webpdemux/libwebpmux/sharpyuv),
#      使 huffman 等目标所需的内部符号(VP8L*/ReadHuffmanCodesHelper 等)可链接;
#   2. 每个 driver #include 上游 xxx_fuzzer.cc,直接调用其被测函数;
#   3. 上游 FuzzTest 框架(google/fuzztest,依赖 abseil)由编译期 shim
#      (fuzztest/fuzztest.h)中性化——域生成由 driver 的显式种子/参数替代,
#      被测函数本体逐字执行。
cmake_minimum_required(VERSION 3.16)
project(fuzzrun C CXX)

# ---- 上游 libwebp 静态构建 ----
set(WEBP_BUILD_ANIM_UTILS OFF CACHE BOOL "" FORCE)
set(WEBP_BUILD_CWEBP OFF CACHE BOOL "" FORCE)
set(WEBP_BUILD_DWEBP OFF CACHE BOOL "" FORCE)
set(WEBP_BUILD_GIF2WEBP OFF CACHE BOOL "" FORCE)
set(WEBP_BUILD_IMG2WEBP OFF CACHE BOOL "" FORCE)
set(WEBP_BUILD_VWEBP OFF CACHE BOOL "" FORCE)
set(WEBP_BUILD_WEBPINFO OFF CACHE BOOL "" FORCE)
set(WEBP_BUILD_WEBPMUX OFF CACHE BOOL "" FORCE)
set(WEBP_BUILD_EXTRAS OFF CACHE BOOL "" FORCE)
set(WEBP_BUILD_FUZZTEST OFF CACHE BOOL "" FORCE)
set(WEBP_BUILD_LIBWEBPMUX ON CACHE BOOL "" FORCE)
set(BUILD_SHARED_LIBS OFF CACHE BOOL "" FORCE)

add_subdirectory(${WEBP_SRC_ROOT} libwebp-src)

# ---- fuzz 目标驱动 ----
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(Threads REQUIRED)

set(FUZZER_DIR ${WEBP_SRC_ROOT}/tests/fuzzer)
include_directories(${WEBP_SRC_ROOT} ${FUZZER_DIR} ${CMAKE_CURRENT_SOURCE_DIR})

set(FUZZ_UTILS_SRC ${FUZZER_DIR}/fuzz_utils.cc)
# pngdec/jpegdec/tiffdec 在无 WEBP_HAVE_* 宏时编译为 return 0 空壳
# (与上游不带 libpng/libjpeg/libtiff 构建工具时一致),满足 image_dec.c
# 的 dispatch 引用;实际语料只走 webp/pnm 阅读器。
set(IMAGEIO_SRC
    ${WEBP_SRC_ROOT}/imageio/image_dec.c
    ${WEBP_SRC_ROOT}/imageio/imageio_util.c
    ${WEBP_SRC_ROOT}/imageio/metadata.c
    ${WEBP_SRC_ROOT}/imageio/webpdec.c
    ${WEBP_SRC_ROOT}/imageio/pnmdec.c
    ${WEBP_SRC_ROOT}/imageio/pngdec.c
    ${WEBP_SRC_ROOT}/imageio/jpegdec.c
    ${WEBP_SRC_ROOT}/imageio/tiffdec.c)

add_executable(fuzz_simple_api drv_simple_api.cc ${FUZZ_UTILS_SRC})
target_link_libraries(fuzz_simple_api webp sharpyuv Threads::Threads m)

add_executable(fuzz_dec drv_dec.cc ${FUZZ_UTILS_SRC})
target_link_libraries(fuzz_dec webp sharpyuv Threads::Threads m)

add_executable(fuzz_webp_info drv_webp_info.cc ${FUZZ_UTILS_SRC} ${IMAGEIO_SRC})
target_link_libraries(fuzz_webp_info webpdemux webp sharpyuv Threads::Threads m)

add_executable(fuzz_huffman drv_huffman.cc ${FUZZ_UTILS_SRC})
target_link_libraries(fuzz_huffman webp sharpyuv Threads::Threads m)

add_executable(fuzz_imageio drv_imageio.cc ${FUZZ_UTILS_SRC} ${IMAGEIO_SRC})
target_link_libraries(fuzz_imageio webpdemux webp sharpyuv Threads::Threads m)

add_executable(fuzz_enc drv_enc.cc ${FUZZ_UTILS_SRC} ${IMAGEIO_SRC})
target_link_libraries(fuzz_enc webpdemux webp sharpyuv Threads::Threads m)

add_executable(fuzz_enc_dec drv_enc_dec.cc ${FUZZ_UTILS_SRC})
target_link_libraries(fuzz_enc_dec webp sharpyuv Threads::Threads m)

add_executable(fuzz_advanced_api drv_advanced_api.cc ${FUZZ_UTILS_SRC})
target_link_libraries(fuzz_advanced_api webp sharpyuv Threads::Threads m)

add_executable(fuzz_animation_api drv_animation_api.cc ${FUZZ_UTILS_SRC})
target_link_libraries(fuzz_animation_api webpdemux webp sharpyuv Threads::Threads m)

add_executable(fuzz_animdecoder drv_animdecoder.cc ${FUZZ_UTILS_SRC} ${IMAGEIO_SRC})
target_link_libraries(fuzz_animdecoder webpdemux webp sharpyuv Threads::Threads m)

add_executable(fuzz_animencoder drv_animencoder.cc ${FUZZ_UTILS_SRC})
target_link_libraries(fuzz_animencoder libwebpmux webp sharpyuv Threads::Threads m)

add_executable(fuzz_mux_demux drv_mux_demux.cc ${FUZZ_UTILS_SRC})
target_link_libraries(fuzz_mux_demux libwebpmux webpdemux webp sharpyuv
                      Threads::Threads m)
