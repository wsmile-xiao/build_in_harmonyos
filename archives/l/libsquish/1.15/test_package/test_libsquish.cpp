// test_libsquish.cpp — real API round-trip test for libsquish
//
// Creates a small RGBA pixel block, compresses it with DXT1 via the squish
// public API, decompresses it back, and verifies the output is valid
// (non-zero bytes) and that the reconstruction error is within a reasonable
// bound. Uses only the portable scalar backend (no SSE on ARM).
#include <squish.h>

#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <cmath>

static int failures = 0;

static void check(int cond, const char *msg) {
    if (cond) {
        std::printf("[ok] %s\n", msg);
    } else {
        std::printf("[FAIL] %s\n", msg);
        ++failures;
    }
}

int main() {
    // 8x8 RGBA image, 4 bytes per pixel.
    const int width = 8;
    const int height = 8;
    const int pixels = width * height;
    const int rgba_size = pixels * 4;

    unsigned char rgba[rgba_size];
    // Fill with a simple gradient so compression has real data to work on.
    for (int i = 0; i < pixels; ++i) {
        rgba[i * 4 + 0] = (unsigned char)((i * 17) & 0xff);       // R
        rgba[i * 4 + 1] = (unsigned char)((i * 31) & 0xff);       // G
        rgba[i * 4 + 2] = (unsigned char)((i * 53) & 0xff);       // B
        rgba[i * 4 + 3] = 255;                                    // A
    }

    // --- Storage requirements (DXT1: 8 bytes per 4x4 block) ---
    const int flags = squish::kDxt1;
    int storage = squish::GetStorageRequirements(width, height, flags);
    int expected_storage = (width / 4) * (height / 4) * 8;  // 8 bytes/block
    check(storage == expected_storage, "GetStorageRequirements returns 32 bytes for 8x8 DXT1");

    // --- Compress ---
    unsigned char *blocks = (unsigned char *)std::malloc(storage);
    std::memset(blocks, 0, storage);
    squish::CompressImage(rgba, width, height, blocks, flags);
    // Compressed output must not be all zeros (real gradient was compressed).
    int nonzero = 0;
    for (int i = 0; i < storage; ++i) {
        if (blocks[i] != 0) { ++nonzero; break; }
    }
    check(nonzero > 0, "CompressImage produced non-zero DXT1 output");

    // --- Decompress round-trip ---
    unsigned char decomp[rgba_size];
    std::memset(decomp, 0, rgba_size);
    squish::DecompressImage(decomp, width, height, blocks, flags);
    int decomp_nonzero = 0;
    for (int i = 0; i < rgba_size; ++i) {
        if (decomp[i] != 0) { ++decomp_nonzero; break; }
    }
    check(decomp_nonzero > 0, "DecompressImage produced non-zero output");

    // --- Reconstruction error (ComputeMSE) ---
    double colourMSE = 0.0, alphaMSE = 0.0;
    squish::ComputeMSE(rgba, width, height, blocks, flags, colourMSE, alphaMSE);
    std::printf("[info] colourMSE=%.2f alphaMSE=%.2f\n", colourMSE, alphaMSE);
    check(colourMSE >= 0.0 && colourMSE < 10000.0, "colourMSE within sane range");
    check(alphaMSE == 0.0, "alphaMSE is zero (DXT1 alpha is opaque)");

    // --- Single-block Compress/Decompress (mask API) ---
    unsigned char block16[16] = {0};
    squish::Compress(rgba, block16, flags);
    int block_nonzero = 0;
    for (int i = 0; i < 8; ++i) {  // DXT1 block = 8 bytes
        if (block16[i] != 0) { ++block_nonzero; break; }
    }
    check(block_nonzero > 0, "Compress (single block) produced non-zero output");

    unsigned char decomp_block[64] = {0};
    squish::Decompress(decomp_block, block16, flags);
    int db_nonzero = 0;
    for (int i = 0; i < 64; ++i) {
        if (decomp_block[i] != 0) { ++db_nonzero; break; }
    }
    check(db_nonzero > 0, "Decompress (single block) produced non-zero output");

    std::free(blocks);

    if (failures > 0) {
        std::printf("RESULT: %d test(s) FAILED\n", failures);
        return 1;
    }
    std::printf("RESULT: all tests passed\n");
    return 0;
}
