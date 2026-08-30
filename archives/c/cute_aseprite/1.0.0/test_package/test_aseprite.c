// test_package for cute_aseprite 1.0.0 — exercises the real public API.
//
// cute_aseprite is a single-file C header. We define
// CUTE_ASEPRITE_IMPLEMENTATION here and drive it through the public API:
//   cute_aseprite_load_from_memory()  -> parse an in-memory .ase file
//   ase->frame_count / w / h / pixels -> inspect parsed fields
//   cute_aseprite_free()              -> release
//
// The test embeds a minimal, structurally valid Aseprite file (1 frame,
// 1 layer, 1 raw RGBA cel, 2x2) built exactly per the v1.00 parser layout
// read from the header (s_read_* order in cute_aseprite_load_from_memory).
//
// Platform note (OHOS): this test is pure C89/C99 + stdlib; it exercises the
// parse path end-to-end and prints HMBS_TEST_PACKAGE_RESULT for CI.
#include "cute_aseprite.h"

#include <stdio.h>
#include <string.h>

static int g_failures = 0;

static void check(int cond, const char* name)
{
  if (cond) {
    printf("PASS: %s\n", name);
  } else {
    printf("FAIL: %s\n", name);
    ++g_failures;
  }
}

static void le16(unsigned char* p, unsigned v) { p[0] = (unsigned char)(v & 0xff); p[1] = (unsigned char)((v >> 8) & 0xff); }
static void le32(unsigned char* p, unsigned v) { p[0] = (unsigned char)(v & 0xff); p[1] = (unsigned char)((v >> 8) & 0xff); p[2] = (unsigned char)((v >> 16) & 0xff); p[3] = (unsigned char)((v >> 24) & 0xff); }

/* Build a minimal valid .ase file: header(128) + frame header(16) +
 * layer chunk + cel chunk (raw RGBA). Returns the buffer length. */
static int build_ase(unsigned char* b)
{
  unsigned char* p = b;

  /* --- Aseprite file header (128 bytes), layout per cute_aseprite v1.00 --- */
  le32(p, 0);            p += 4;   /* file size (skipped by parser) */
  le16(p, 0xA5E0);       p += 2;   /* magic */
  le16(p, 1);            p += 2;   /* frame_count = 1 */
  le16(p, 2);            p += 2;   /* width = 2 */
  le16(p, 2);            p += 2;   /* height = 2 */
  le16(p, 32);           p += 2;   /* bpp = 32/8 = 4 -> RGBA */
  le32(p, 0);            p += 4;   /* flags: no embedded color profile */
  le16(p, 100);          p += 2;   /* speed = 100ms (default frame duration) */
  le32(p, 0);            p += 4;   /* reserved (zeroed) */
  le32(p, 0);            p += 4;   /* reserved (zeroed) */
  *p++ = 0;                        /* transparent palette index */
  p += 3;                          /* reserved (zeroed) */
  le16(p, 0);            p += 2;   /* number of colors */
  *p++ = 0;                        /* pixel width */
  *p++ = 0;                        /* pixel height */
  le16(p, 0);            p += 2;   /* grid x */
  le16(p, 0);            p += 2;   /* grid y */
  le16(p, 0);            p += 2;   /* grid w */
  le16(p, 0);            p += 2;   /* grid h */
  p += 84;                         /* reserved for future use */
  /* header now spans 128 bytes */

  /* --- Frame header (16 bytes) --- */
  le32(p, 0);            p += 4;   /* frame size (skipped) */
  le16(p, 0xF1FA);       p += 2;   /* frame magic */
  le16(p, 2);            p += 2;   /* chunk_count = 2 (layer + cel) */
  le16(p, 100);          p += 2;   /* duration ms */
  p += 2;                          /* reserved (zeroed) */
  le32(p, 0);            p += 4;   /* new_chunk_count (0 -> keep 2) */

  /* --- Layer chunk (0x2004) --- */
  le32(p, 0);            p += 4;   /* chunk_size placeholder */
  le16(p, 0x2004);       p += 2;   /* chunk_type */
  le16(p, 0);            p += 2;   /* flags */
  le16(p, 0);            p += 2;   /* type = normal (0) */
  le16(p, 0);            p += 2;   /* child_level */
  le16(p, 0);            p += 2;   /* default width (ignored) */
  le16(p, 0);            p += 2;   /* default height (ignored) */
  le16(p, 0);            p += 2;   /* blend_mode = normal */
  *p++ = 255;                      /* opacity */
  p += 3;                          /* reserved (zeroed) */
  le16(p, 1);            p += 2;   /* name length (u16, s_read_string reads u16) */
  *p++ = 'L';                      /* name "L" */
  /* layer chunk payload = flags(2)+type(2)+child(2)+dw(2)+dh(2)+blend(2)
   * +opacity(1)+reserved(3)+name_len(2)+name(1) = 19; chunk_size counts
   * size+type too, so total = 19+6 = 25. chunk_size field is at
   * header(128)+frame(16)=offset 144. */
  le32(b + 128 + 16, 25);

  /* --- Cel chunk (0x2005), raw (type 0) RGBA 2x2 --- */
  le32(p, 0);            p += 4;   /* chunk_size placeholder */
  le16(p, 0x2005);       p += 2;   /* chunk_type */
  le16(p, 0);            p += 2;   /* layer_index = 0 */
  le16(p, 0);            p += 2;   /* x = 0 */
  le16(p, 0);            p += 2;   /* y = 0 */
  *p++ = 255;                      /* opacity */
  le16(p, 0);            p += 2;   /* cel_type = 0 (raw) */
  p += 7;                          /* reserved (zeroed) */
  le16(p, 2);            p += 2;   /* cel w = 2 */
  le16(p, 2);            p += 2;   /* cel h = 2 */
  {                                /* raw RGBA pixel data 2*2*4 = 16 bytes */
    unsigned i;
    for (i = 0; i < 16; ++i) *p++ = (unsigned char)(0x40 + i);
  }
  /* cel chunk payload = layer_idx(2)+x(2)+y(2)+opacity(1)+type(2)+reserved(7)
   * +w(2)+h(2)+pixels(16) = 36; +size+type(6) = 42.
   * cel chunk starts at 144+25 = offset 169. */
  le32(b + 128 + 16 + 25, 42);

  return (int)(p - b);
}

int main(void)
{
  unsigned char buf[512];
  int size = build_ase(buf);

  /* Structurally valid .ase must parse without assertion/leak. */
  ase_t* ase = cute_aseprite_load_from_memory(buf, size, NULL);
  check(ase != NULL, "cute_aseprite_load_from_memory returns non-NULL for valid .ase");

  if (ase) {
    check(ase->frame_count == 1, "frame_count == 1");
    check(ase->w == 2 && ase->h == 2, "w/h == 2x2");
    check(ase->layer_count == 1, "layer_count == 1");
    if (ase->frame_count >= 1) {
      ase_frame_t* f = ase->frames + 0;
      check(f->cel_count == 1, "frame[0] cel_count == 1");
      check(f->duration_milliseconds == 100, "frame[0] duration == 100ms");
      if (f->cel_count >= 1 && f->cels[0].pixels) {
        /* First RGBA pixel must round-trip from our embedded 0x40..0x4f data.
         * v1.00 cel->pixels is void*; cast to unsigned char* to index. */
        const unsigned char* px = (const unsigned char*)f->cels[0].pixels;
        check(px[0] == 0x40, "cel pixel[0] == 0x40");
        check(px[15] == 0x4f, "cel pixel[15] == 0x4f");
      } else {
        check(0, "cel pixels allocated");
      }
    }
    cute_aseprite_free(ase);
  }

  printf("HMBS_TEST_PACKAGE_RESULT: %s (%d failures)\n",
         g_failures == 0 ? "PASS" : "FAIL", g_failures);
  return g_failures == 0 ? 0 : 1;
}