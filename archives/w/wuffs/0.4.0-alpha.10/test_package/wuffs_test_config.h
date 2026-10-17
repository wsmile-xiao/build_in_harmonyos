// Copyright 2026 The OpenHarmony PC adaptation authors.
//
// SPDX-License-Identifier: Apache-2.0 OR MIT
//
// ----------------

// Shared configuration for the wuffs test_package consumers.
//
// wuffs ships as a "single file C library": one file that acts as a header
// unless WUFFS_IMPLEMENTATION is defined before it is included. This header is
// included by three translation units:
//
//   test_wuffs.c                  - defines WUFFS_IMPLEMENTATION first (the
//                                   one TU that carries the implementation)
//   test_wuffs_header_only_tu.c   - includes it in plain header mode
//   test_wuffs_cpp.cpp            - same, from C++
//
// They must agree on WUFFS_CONFIG__MODULE* (those select which parts of the
// library are declared/compiled), so the definitions live here.
//
// The module list mirrors upstream's own PNG test (test/c/std/png.c): the PNG
// decoder needs the base I/O layer, adler32, CRC-32, deflate and zlib.

#ifndef WUFFS_TEST_PACKAGE_CONFIG_H
#define WUFFS_TEST_PACKAGE_CONFIG_H

#include <stdint.h>

#define WUFFS_CONFIG__MODULES
#define WUFFS_CONFIG__MODULE__ADLER32
#define WUFFS_CONFIG__MODULE__BASE
#define WUFFS_CONFIG__MODULE__CRC32
#define WUFFS_CONFIG__MODULE__DEFLATE
#define WUFFS_CONFIG__MODULE__PNG
#define WUFFS_CONFIG__MODULE__ZLIB

// Installed by this Conan package as include/wuffs/wuffs-v0.4.c.
#include <wuffs/wuffs-v0.4.c>

#ifdef __cplusplus
extern "C" {
#endif

// Defined in test_wuffs_header_only_tu.c (header mode, no implementation):
// proves the packaged file is usable as a header from a second translation
// unit of the same program.
uint32_t header_only_tu_crc32_of_png(void);

// Defined in test_wuffs_cpp.cpp (C++): proves the packaged file is usable from
// C++ and that the C++ TU links against the C implementation TU.
uint32_t cpp_tu_crc32_of_decoded_rgb(void);

#ifdef __cplusplus
}  // extern "C"
#endif

#endif  // WUFFS_TEST_PACKAGE_CONFIG_H
