// test_crn.cpp — consumer test for crunch-dxtc (R34: real API usage).
//
// Exercises the installed libcrn public API (inc/crnlib.h):
//   1-2. string helpers (format string, CRN file extension)
//   3-5. format property queries (bytes per DXT block, bits per texel)
//   6.   single-block DXT1 compress -> decompress round-trip on a uniform
//        4x4 block (lossless for a solid color; exact pixel equality)
//   7.   DXT quality string helper
//   8.   writes test_input.tga (16x16) used by the CLI conversion check
//
// Every check prints "ok N - ..." and any failure prints "FAIL ..." and
// returns non-zero. No conditional skips: exit 0 means all 8 checks ran.

#include <crnlib.h>

#include <cstdio>
#include <cstring>

static int g_failed = 0;
static int g_index = 0;

#define CHECK(cond, desc)                                   \
  do {                                                      \
    ++g_index;                                              \
    if (cond) {                                             \
      printf("ok %d - %s\n", g_index, desc);                \
    } else {                                                \
      printf("FAIL %d - %s\n", g_index, desc);              \
      g_failed = 1;                                         \
    }                                                       \
  } while (0)

// Minimal uncompressed 24-bit TGA writer (18-byte header + BGR pixels).
static bool write_tga(const char* path, int width, int height) {
  FILE* f = fopen(path, "wb");
  if (!f) {
    return false;
  }
  unsigned char header[18];
  memset(header, 0, sizeof(header));
  header[2] = 2;  // uncompressed true-color
  header[12] = (unsigned char)(width & 0xFF);
  header[13] = (unsigned char)((width >> 8) & 0xFF);
  header[14] = (unsigned char)(height & 0xFF);
  header[15] = (unsigned char)((height >> 8) & 0xFF);
  header[16] = 24;  // bits per pixel
  if (fwrite(header, 1, sizeof(header), f) != sizeof(header)) {
    fclose(f);
    return false;
  }
  for (int y = 0; y < height; ++y) {
    for (int x = 0; x < width; ++x) {
      unsigned char px[3];
      px[0] = (unsigned char)((x * 255) / (width - 1));   // B
      px[1] = (unsigned char)((y * 255) / (height - 1));  // G
      px[2] = 128;                                        // R
      if (fwrite(px, 1, 3, f) != 3) {
        fclose(f);
        return false;
      }
    }
  }
  fclose(f);
  return true;
}

int main() {
  // 1. Format string helper returns a usable name.
  const char* fmt_str = crn_get_format_string(cCRNFmtDXT1);
  CHECK(fmt_str && fmt_str[0] != '\0', "crn_get_format_string(DXT1) non-empty");
  if (fmt_str) {
    printf("info: DXT1 format string is \"%s\"\n", fmt_str);
  }

  // 2. CRN file extension helper (literal in crnlib.cpp).
  const char* ext = crn_get_file_type_ext(cCRNFileTypeCRN);
  CHECK(ext && strcmp(ext, "crn") == 0, "crn_get_file_type_ext(CRN) == crn");

  // 3-5. DXT format geometry queries (DXT spec constants).
  CHECK(crn_get_bytes_per_dxt_block(cCRNFmtDXT1) == 8, "DXT1 block is 8 bytes");
  CHECK(crn_get_bytes_per_dxt_block(cCRNFmtDXT5) == 16, "DXT5 block is 16 bytes");
  CHECK(crn_get_format_bits_per_texel(cCRNFmtDXT1) == 4, "DXT1 is 4 bits per texel");

  // 6. One-block DXT1 compress -> decompress round-trip.
  {
    crn_comp_params params;  // defaults: format DXT1
    params.m_dxt_quality = cCRNDXTQualityFast;
    crn_block_compressor_context_t ctx = crn_create_block_compressor(params);
    bool roundtrip_ok = false;
    if (ctx) {
      crn_uint32 pixels[16];
      for (int i = 0; i < 16; ++i) {
        // r,g,b,a with r first in memory (little-endian packing below).
        // Pure red is exactly representable in RGB565, so a uniform block
        // must round-trip bit-exact through DXT1.
        crn_uint8 r = 255, g = 0, b = 0, a = 255;
        pixels[i] = (crn_uint32)r | ((crn_uint32)g << 8) |
                    ((crn_uint32)b << 16) | ((crn_uint32)a << 24);
      }
      crn_uint8 block[8];
      memset(block, 0, sizeof(block));
      crn_compress_block(ctx, pixels, block);
      crn_free_block_compressor(ctx);
      crn_uint32 out[16];
      memset(out, 0, sizeof(out));
      if (crn_decompress_block(block, out, cCRNFmtDXT1)) {
        roundtrip_ok = (memcmp(pixels, out, sizeof(pixels)) == 0);
      }
    }
    CHECK(roundtrip_ok, "DXT1 block compress/decompress round-trip exact");
  }

  // 7. DXT quality string helper returns a usable name.
  const char* qstr = crn_get_dxt_quality_string(cCRNDXTQualityUber);
  CHECK(qstr && qstr[0] != '\0', "crn_get_dxt_quality_string(Uber) non-empty");

  // 8. Fixture for the CLI conversion check below.
  CHECK(write_tga("test_input.tga", 16, 16), "write test_input.tga fixture");

  if (g_failed == 0) {
    printf("All 8 libcrn checks passed\n");
  }
  return g_failed;
}
