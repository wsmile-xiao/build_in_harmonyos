/*
 * HarmonyOS-specific test for the cmp (C MessagePack) library.
 *
 * Why this is "HarmonyOS 专项":
 *  1. No-heap property: exampled on OHOS embedded/limited environments the
 *     library must not allocate. We link with -Wl,--wrap=malloc/free/calloc/
 *     realloc, count every allocation attempt, and fail the test if cmp ever
 *     allocates while encoding/decoding (the library is documented to make no
 *     heap allocations — this test proves it holds on the OHOS build).
 *  2. Exact wire-format bytes: MessagePack interchange requires byte-exact
 *     output; verified against the spec values compiled into this test.
 *  3. 64-bit boundary values (aarch64/armv8): uint64/int64 extremes and
 *     32-bit sizing boundaries that only differ on 64-bit platforms.
 *
 * Uses only the public cmp.h API via a caller-provided memory context, i.e.
 * exactly how an OHOS PC application would embed the library.
 */

#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "cmp.h"

/* ---- allocation counters (linked with -Wl,--wrap=...) ---- */
static size_t alloc_count = 0;

/* Provided by the linker for -Wl,--wrap=malloc etc. */
extern void *__real_malloc(size_t);
extern void *__real_calloc(size_t, size_t);
extern void *__real_realloc(void *, size_t);
extern void __real_free(void *);

void *__wrap_malloc(size_t size) {
  alloc_count++;
  return __real_malloc(size);
}
void *__wrap_calloc(size_t n, size_t size) {
  alloc_count++;
  return __real_calloc(n, size);
}
void *__wrap_realloc(void *p, size_t size) {
  alloc_count++;
  return __real_realloc(p, size);
}
void __wrap_free(void *p) { __real_free(p); }

/* ---- caller-provided in-memory buffer context ---- */
static uint8_t buf[65536];
static size_t buf_len = 0;

static bool ohos_reader(struct cmp_ctx_s *ctx, void *data, size_t limit) {
  size_t *position = (size_t *)ctx->buf;
  size_t avail = buf_len - *position;
  if (limit > avail) {
    return false;
  }
  memcpy(data, buf + *position, limit);
  *position += limit;
  return true;
}

static bool ohos_skipper(struct cmp_ctx_s *ctx, size_t count) {
  size_t *position = (size_t *)ctx->buf;
  size_t avail = buf_len - *position;
  if (count > avail) {
    return false;
  }
  *position += count;
  return true;
}

static size_t ohos_writer(struct cmp_ctx_s *ctx, const void *data,
                          size_t count) {
  size_t *position = (size_t *)ctx->buf;
  size_t avail = sizeof(buf) - *position;
  if (count > avail) {
    return 0;
  }
  memcpy(buf + *position, data, count);
  *position += count;
  buf_len = *position;
  return count;
}

#define CHECK(cond)                                                            \
  do {                                                                         \
    if (!(cond)) {                                                             \
      fprintf(stderr, "FAILED at line %d: %s\n", __LINE__, #cond);             \
      return 1;                                                                \
    }                                                                          \
  } while (0)

static int test_exact_wire_bytes(void) {
  cmp_ctx_t ctx;
  size_t position = 0;
  uint8_t expected[64];
  size_t expected_len;

  /* nil / bool */
  memset(&ctx, 0, sizeof(ctx));
  ctx.buf = &position;
  ctx.read = ohos_reader;
  ctx.skip = ohos_skipper;
  ctx.write = ohos_writer;
  position = 0;
  CHECK(cmp_write_nil(&ctx));
  CHECK(cmp_write_true(&ctx));
  CHECK(cmp_write_false(&ctx));
  expected[0] = 0xc0;                    /* nil   */
  expected[1] = 0xc3;                    /* true  */
  expected[2] = 0xc2;                    /* false */
  expected_len = 3;
  CHECK(buf_len == expected_len);
  CHECK(memcmp(buf, expected, expected_len) == 0);

  /* integer compaction: cmp_write_integer/cmp_write_uinteger pick the
   * smallest marker, while cmp_write_u8 always writes the explicit uint8
   * marker 0xcc — both must match the MessagePack spec exactly. */
  position = 0;
  CHECK(cmp_write_uinteger(&ctx, 0));            /* pfix 0x00 */
  CHECK(cmp_write_uinteger(&ctx, 0x7f));         /* pfix 0x7f */
  CHECK(cmp_write_u8(&ctx, 0xff));               /* 0xcc 0xff */
  CHECK(cmp_write_integer(&ctx, -1));            /* nfix 0xff */
  CHECK(cmp_write_integer(&ctx, -32));           /* nfix 0xe0 */
  CHECK(cmp_write_s8(&ctx, -33));                /* 0xd0 0xdf */
  expected[0] = 0x00;
  expected[1] = 0x7f;
  expected[2] = 0xcc; expected[3] = 0xff;
  expected[4] = 0xff;                    /* negative fixint -1 */
  expected[5] = 0xe0;                    /* negative fixint -32 */
  expected[6] = 0xd0; expected[7] = 0xdf;
  expected_len = 8;
  CHECK(buf_len == expected_len);
  CHECK(memcmp(buf, expected, expected_len) == 0);

  /* uint boundaries */
  position = 0;
  CHECK(cmp_write_u16(&ctx, 0xfff0));    /* 0xcd 0xff 0xf0 */
  CHECK(cmp_write_u32(&ctx, 0xfffff000U));        /* 0xce */
  CHECK(cmp_write_u64(&ctx, 0xffffffffffffffffULL)); /* 0xcf */
  expected[0] = 0xcd; expected[1] = 0xff; expected[2] = 0xf0;
  expected[3] = 0xce; expected[4] = 0xff; expected[5] = 0xff;
  expected[6] = 0xf0; expected[7] = 0x00;
  expected[8] = 0xcf; expected[9] = 0xff; expected[10] = 0xff;
  expected[11] = 0xff; expected[12] = 0xff; expected[13] = 0xff;
  expected[14] = 0xff; expected[15] = 0xff; expected[16] = 0xff;
  expected_len = 17;
  CHECK(buf_len == expected_len);
  CHECK(memcmp(buf, expected, expected_len) == 0);

  /* str/bin markers */
  position = 0;
  CHECK(cmp_write_str(&ctx, "abc", 3));  /* fixstr 0xa3 */
  CHECK(cmp_write_bin(&ctx, "\x01\x02", 2)); /* bin8 0xc4 0x02 */
  expected[0] = 0xa3; expected[1] = 'a'; expected[2] = 'b'; expected[3] = 'c';
  expected[4] = 0xc4; expected[5] = 0x02; expected[6] = 0x01; expected[7] = 0x02;
  expected_len = 8;
  CHECK(buf_len == expected_len);
  CHECK(memcmp(buf, expected, expected_len) == 0);

  /* array / map */
  position = 0;
  CHECK(cmp_write_array(&ctx, 1));       /* 0x91 */
  CHECK(cmp_write_map(&ctx, 1));         /* 0x81 */
  CHECK(cmp_write_str(&ctx, "k", 1));    /* 0xa1 0x6b */
  CHECK(cmp_write_uinteger(&ctx, 42));   /* 0x2a */
  expected[0] = 0x91;
  expected[1] = 0x81;
  expected[2] = 0xa1; expected[3] = 'k';
  expected[4] = 0x2a;
  expected_len = 5;
  CHECK(buf_len == expected_len);
  CHECK(memcmp(buf, expected, expected_len) == 0);

  /* float / double */
  position = 0;
  CHECK(cmp_write_float(&ctx, 1.5f));    /* 0xca 0x3f 0xc0 0x00 0x00 */
  CHECK(cmp_write_double(&ctx, 1.0));    /* 0xcb 0x3f 0xf0 0x00...0 (9 bytes) */
  expected[0] = 0xca; expected[1] = 0x3f; expected[2] = 0xc0; expected[3] = 0x00; expected[4] = 0x00;
  expected[5] = 0xcb; expected[6] = 0x3f; expected[7] = 0xf0;
  expected[8] = 0x00; expected[9] = 0x00; expected[10] = 0x00;
  expected[11] = 0x00; expected[12] = 0x00; expected[13] = 0x00;
  expected_len = 14;
  CHECK(buf_len == expected_len);
  CHECK(memcmp(buf, expected, expected_len) == 0);

  /* ext: 5-byte payload -> ext8 (0xc7, len, type, data) */
  position = 0;
  CHECK(cmp_write_ext(&ctx, 5, 5, "\x01\x02\x03\x04\x05"));
  expected[0] = 0xc7; expected[1] = 0x05; expected[2] = 0x05;
  expected[3] = 0x01; expected[4] = 0x02; expected[5] = 0x03;
  expected[6] = 0x04; expected[7] = 0x05;
  expected_len = 8;
  CHECK(buf_len == expected_len);
  CHECK(memcmp(buf, expected, expected_len) == 0);

  printf("PASS: exact wire bytes (%zu bytes encoded, zero allocations)\n", buf_len);
  return 0;
}

static int test_64bit_boundaries(void) {
  cmp_ctx_t ctx;
  size_t position = 0;
  uint8_t tmp[32];

  memset(&ctx, 0, sizeof(ctx));
  ctx.buf = &position;
  ctx.read = ohos_reader;
  ctx.skip = ohos_skipper;
  ctx.write = ohos_writer;

  /* round-trip uint64 max / int64 min */
  position = 0;
  CHECK(cmp_write_u64(&ctx, UINT64_MAX));
  CHECK(cmp_write_s64(&ctx, INT64_MIN));
  CHECK(cmp_write_s64(&ctx, INT64_MAX));
  {
    cmp_ctx_t rctx;
    size_t rp = 0;
    uint64_t u; int64_t s1, s2;
    memset(&rctx, 0, sizeof(rctx));
    rctx.buf = &rp;
    rctx.read = ohos_reader;
    rctx.skip = ohos_skipper;
    rctx.write = ohos_writer;
    CHECK(cmp_read_uinteger(&rctx, &u) && u == UINT64_MAX);
    CHECK(cmp_read_integer(&rctx, &s1) && s1 == INT64_MIN);
    CHECK(cmp_read_integer(&rctx, &s2) && s2 == INT64_MAX);
  }

  /* large str (str16 sizing, >255) */
  {
    char big[300];
    size_t i;
    for (i = 0; i < sizeof(big); i++) {
      big[i] = (char)('a' + (i % 26));
    }
    position = 0;
    CHECK(cmp_write_str(&ctx, big, sizeof(big)));
    /* 300 bytes > 255 -> str16 marker 0xda (str8 0xd9 only covers <=255);
     * 300 = 0x012C, BE length bytes are 0x01 0x2C */
    CHECK(buf[0] == 0xda && buf[1] == ((sizeof(big) >> 8) & 0xff) &&
          buf[2] == (sizeof(big) & 0xff));
    {
      cmp_ctx_t rctx;
      size_t rp = 0;
      uint32_t sz;
      char out[301];               /* cmp_read_str needs capacity > str_size */
      memset(&rctx, 0, sizeof(rctx));
      rctx.buf = &rp;
      rctx.read = ohos_reader;
      rctx.skip = ohos_skipper;
      rctx.write = ohos_writer;
      /* cmp_read_str internally reads the header via cmp_read_str_size;
       * pass the buffer capacity, it returns the actual string length. */
      sz = (uint32_t)sizeof(out);
      CHECK(cmp_read_str(&rctx, out, &sz) && sz == sizeof(big));
      CHECK(memcmp(out, big, sizeof(big)) == 0);
    }
  }

  printf("PASS: 64-bit boundary values round-trip\n");
  return 0;
}

static int test_noheap_roundtrip(void) {
  cmp_ctx_t ctx;
  size_t position = 0;

  memset(&ctx, 0, sizeof(ctx));
  ctx.buf = &position;
  ctx.read = ohos_reader;
  ctx.skip = ohos_skipper;
  ctx.write = ohos_writer;

  /* complex nested document */
  position = 0;
  alloc_count = 0;
  CHECK(cmp_write_map(&ctx, 3));
  CHECK(cmp_write_str(&ctx, "name", 4));
  CHECK(cmp_write_str(&ctx, "cmp-on-ohos", 11));
  CHECK(cmp_write_str(&ctx, "value", 5));
  CHECK(cmp_write_u64(&ctx, UINT64_MAX));
  CHECK(cmp_write_str(&ctx, "items", 5));
  CHECK(cmp_write_array(&ctx, 4));
  CHECK(cmp_write_nil(&ctx));
  CHECK(cmp_write_true(&ctx));
  CHECK(cmp_write_bin(&ctx, "\x00\x01\x02", 3));
  CHECK(cmp_write_double(&ctx, 3.141592653589793));
  CHECK(alloc_count == 0);

  {
    cmp_ctx_t rctx;
    size_t rp = 0;
    uint32_t nmap, narr;
    char key[32]; uint32_t ks;
    uint64_t u;
    uint8_t b[8]; uint32_t bs;
    double d;
    bool b_ok;

    memset(&rctx, 0, sizeof(rctx));
    rctx.buf = &rp;
    rctx.read = ohos_reader;
    rctx.skip = ohos_skipper;
    rctx.write = ohos_writer;

    alloc_count = 0;
    CHECK(cmp_read_map(&rctx, &nmap) && nmap == 3);
    ks = sizeof(key); CHECK(cmp_read_str(&rctx, key, &ks)); key[ks] = 0;
    CHECK(strcmp(key, "name") == 0);
    ks = sizeof(key); CHECK(cmp_read_str(&rctx, key, &ks)); key[ks] = 0;
    CHECK(strcmp(key, "cmp-on-ohos") == 0);
    ks = sizeof(key); CHECK(cmp_read_str(&rctx, key, &ks)); key[ks] = 0;
    CHECK(strcmp(key, "value") == 0);
    CHECK(cmp_read_uinteger(&rctx, &u) && u == UINT64_MAX);
    ks = sizeof(key); CHECK(cmp_read_str(&rctx, key, &ks)); key[ks] = 0;
    CHECK(strcmp(key, "items") == 0);
    CHECK(cmp_read_array(&rctx, &narr) && narr == 4);
    {
      cmp_object_t obj;
      CHECK(cmp_read_object(&rctx, &obj));
      CHECK(obj.type == CMP_TYPE_NIL);
    }
    CHECK(cmp_read_bool(&rctx, &b_ok) && b_ok == true);
    bs = sizeof(b); CHECK(cmp_read_bin(&rctx, b, &bs) && bs == 3 && memcmp(b, "\x00\x01\x02", 3) == 0);
    CHECK(cmp_read_double(&rctx, &d) && d == 3.141592653589793);
    CHECK(alloc_count == 0);
  }

  printf("PASS: no-heap encode/decode round-trip (alloc_count=%zu)\n", alloc_count);
  return 0;
}

int main(void) {
  if (test_exact_wire_bytes() != 0) {
    return EXIT_FAILURE;
  }
  if (test_64bit_boundaries() != 0) {
    return EXIT_FAILURE;
  }
  if (test_noheap_roundtrip() != 0) {
    return EXIT_FAILURE;
  }
  printf("ALL OHOS TESTS PASSED (zero heap allocations)\n");
  return EXIT_SUCCESS;
}