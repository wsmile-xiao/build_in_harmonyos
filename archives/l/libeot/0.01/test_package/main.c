/* Consumer test for the libeot package (HarmonyOS PC adaptation).
 *
 * Links against the packaged libeot and exercises the real public API:
 *   EOTfillMetadata / EOTgetMetadataLength / EOTcanLegallyEdit /
 *   EOT2ttf_buffer / EOTfreeBuffer / EOTfreeMetadata / EOTprintError
 *
 * The EOT fixture is built in-source: an EOT v1 header (100 bytes, no
 * MicroType compression, no XOR encryption) wrapping a small TrueType
 * payload.  In this uncompressed configuration libeot must parse the
 * metadata and hand back the font data byte-identical.  A second fixture
 * carries a non-empty UTF-16 family name to exercise the string parser,
 * and truncated / corrupt inputs must fail with the documented error codes.
 *
 * The program also writes fixture.eot (for the packaged eot2ttf tool, run
 * by test_package/conanfile.py) and expected.ttf (the payload, for a
 * byte-wise comparison of the tool's output).
 */

#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include <libeot/libeot.h>

/* --- deterministic TrueType skeleton (offset table + 4 table records) --- */
static const uint8_t TTF_PAYLOAD[] = {
    0x00, 0x01, 0x00, 0x00, /* sfnt version 1.0 */
    0x00, 0x04,             /* numTables: cmap, glyf, head, loca */
    0x00, 0x10,             /* searchRange */
    0x00, 0x02,             /* entrySelector */
    0x00, 0x00,             /* rangeShift */
    /* table records */
    'c',  'm',  'a',  'p',  0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x70, 0x00, 0x00, 0x00, 0x10,
    'g',  'l',  'y',  'f',  0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x80, 0x00, 0x00, 0x00, 0x20,
    'h',  'e',  'a',  'd',  0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0xA0, 0x00, 0x00, 0x00, 0x36,
    'l',  'o',  'c',  'a',  0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0xD8, 0x00, 0x00, 0x00, 0x08,
    /* cmap (4 bytes) */ 0x00, 0x00, 0x00, 0x01,
    /* glyf (32 bytes of glyph data) */
    0x00, 0x01, 0x00, 0x02, 0x00, 0x03, 0x00, 0x04, 0x00, 0x05, 0x00, 0x06, 0x00, 0x07, 0x00, 0x08,
    0x00, 0x09, 0x00, 0x0A, 0x00, 0x0B, 0x00, 0x0C, 0x00, 0x0D, 0x00, 0x0E, 0x00, 0x0F, 0x00, 0x10,
    /* head (54 bytes) */
    0x00, 0x01, 0x00, 0x00, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x10, 0x00, 0x00, 0x00,
    0x00, 0x00, 0x00, 0x00, 0xDE, 0xAD, 0xBE, 0xEF, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x04, 0x00, 0x00, 0x00, 0x00, 0x00,
    /* loca (8 bytes) */
    0x00, 0x00, 0x00, 0x10, 0x00, 0x00, 0x00, 0x20
};
#define PAYLOAD_LEN ((unsigned)(sizeof(TTF_PAYLOAD) / sizeof(TTF_PAYLOAD[0])))

static unsigned putU32(uint8_t *p, uint32_t v)
{
  p[0] = (uint8_t)(v & 0xff);
  p[1] = (uint8_t)((v >> 8) & 0xff);
  p[2] = (uint8_t)((v >> 16) & 0xff);
  p[3] = (uint8_t)((v >> 24) & 0xff);
  return 4;
}

static unsigned putU16(uint8_t *p, uint16_t v)
{
  p[0] = (uint8_t)(v & 0xff);
  p[1] = (uint8_t)((v >> 8) & 0xff);
  return 2;
}

/* EOT v1 header with empty name strings: exactly 96 bytes, followed by the
 * font data; EOTfillMetadata must report fontDataOffset == 96.
 *
 * Layout note: libeot 0.01 reads CheckSumAdjustment without advancing its
 * scanner and then skips 22 bytes from the field's start, so the four
 * checksum bytes are part of that skip; the name-string size fields sit at
 * offsets 82/86/90/94 and the header ends at 96. */
#define EOT_HEADER_LEN 96u

static unsigned buildEotHeader(uint8_t *h, uint32_t flags, unsigned nameExtra)
{
  unsigned o = 0;
  memset(h, 0, 128);
  o += putU32(h + o, EOT_HEADER_LEN + nameExtra + PAYLOAD_LEN); /* EOTSize */
  o += putU32(h + o, PAYLOAD_LEN);       /* FontDataSize */
  o += putU32(h + o, 0x00010000u);       /* Version magic = VERSION_1 */
  o += putU32(h + o, flags);             /* Flags */
  for (unsigned k = 0; k < 10; ++k)      /* PANOSE */
  {
    h[o++] = 0;
  }
  h[o++] = 1;                       /* Charset = DEFAULT_CHARSET */
  h[o++] = 0;                       /* Italic */
  o += putU32(h + o, 400);          /* Weight */
  o += putU16(h + o, 0);            /* Permissions: 0 = editable */
  o += putU16(h + o, 0x504Cu);      /* MagicNumber */
  for (unsigned k = 0; k < 4; ++k)  /* UnicodeRange */
  {
    o += putU32(h + o, 0);
  }
  for (unsigned k = 0; k < 2; ++k)  /* CodePageRange */
  {
    o += putU32(h + o, 0);
  }
  o += putU32(h + o, 0);            /* CheckSumAdjustment (inside the skip) */
  for (unsigned k = 0; k < 18; ++k) /* remaining reserved/padding bytes */
  {
    h[o++] = 0;
  }
  o += putU16(h + o, (uint16_t)nameExtra); /* FamilyNameSize (UTF-16 bytes) */
  if (nameExtra > 0)                       /* the name itself: "Test" */
  {
    const uint8_t name[] = {'T', 0, 'e', 0, 's', 0, 't', 0};
    memcpy(h + o, name, nameExtra);
    o += nameExtra;
  }
  o += 2;                /* Padding */
  o += putU16(h + o, 0); /* StyleNameSize = 0 */
  o += 2;                /* Padding */
  o += putU16(h + o, 0); /* VersionNameSize = 0 */
  o += 2;                /* Padding */
  o += putU16(h + o, 0); /* FullNameSize = 0 */
  return o; /* == 96 + nameExtra */
}

static uint8_t *buildEot(unsigned *totalLen, uint32_t flags, unsigned nameExtra)
{
  uint8_t header[128];
  unsigned headerLen = buildEotHeader(header, flags, nameExtra);
  if (headerLen != EOT_HEADER_LEN + nameExtra)
  {
    fprintf(stderr, "fixture bug: header length %u != %u\n", headerLen,
        EOT_HEADER_LEN + nameExtra);
    return NULL;
  }
  uint8_t *eot = (uint8_t *)malloc(headerLen + PAYLOAD_LEN);
  if (!eot)
  {
    return NULL;
  }
  memcpy(eot, header, headerLen);
  memcpy(eot + headerLen, TTF_PAYLOAD, PAYLOAD_LEN);
  *totalLen = headerLen + PAYLOAD_LEN;
  return eot;
}

static int g_checks = 0;
#define CHECK(cond, name)                                          \
  do                                                               \
  {                                                                \
    if (!(cond))                                                   \
    {                                                              \
      fprintf(stderr, "FAILED check %d: %s\n", g_checks + 1, name);\
      return 1;                                                    \
    }                                                              \
    ++g_checks;                                                    \
  } while (0)

static int writeFile(const char *name, const uint8_t *data, unsigned len)
{
  FILE *f = fopen(name, "wb");
  if (!f)
  {
    return 0;
  }
  size_t written = fwrite(data, 1, len, f);
  fclose(f);
  return written == len;
}

int main(void)
{
  /* --- fixture A: v1 header, flags = 0 (uncompressed, unencrypted) --- */
  unsigned eotLen = 0;
  uint8_t *eot = buildEot(&eotLen, 0, 0);
  CHECK(eot != NULL, "fixture construction");

  struct EOTMetadata meta;
  enum EOTError rc = EOTfillMetadata(eot, eotLen, &meta);
  CHECK(rc == EOT_SUCCESS, "EOTfillMetadata returns EOT_SUCCESS");
  CHECK(meta.version == VERSION_1, "parsed EOT version is 1");
  CHECK(meta.fontDataSize == PAYLOAD_LEN, "fontDataSize matches payload");
  CHECK(meta.fontDataOffset == EOT_HEADER_LEN, "fontDataOffset is the 96-byte header");
  CHECK(meta.flags == 0, "flags parsed as 0");
  CHECK(meta.weight == 400, "weight parsed as 400");
  CHECK(EOTcanLegallyEdit(&meta), "permissions 0 means legally editable");
  CHECK(EOTgetMetadataLength(eot) == EOT_HEADER_LEN, "metadata length is the 96-byte header");

  uint8_t *converted = NULL;
  unsigned convertedLen = 0;
  struct EOTMetadata metaConv;
  rc = EOT2ttf_buffer(eot, eotLen, &metaConv, &converted, &convertedLen);
  CHECK(rc == EOT_SUCCESS, "EOT2ttf_buffer returns EOT_SUCCESS");
  CHECK(converted != NULL, "conversion produced a buffer");
  CHECK(convertedLen == PAYLOAD_LEN, "converted length matches payload");
  CHECK(converted != NULL && memcmp(converted, TTF_PAYLOAD, PAYLOAD_LEN) == 0,
        "converted bytes are identical to the payload");
  if (converted)
  {
    EOTfreeBuffer(converted);
  }
  EOTfreeMetadata(&metaConv);
  CHECK(1, "EOTfreeBuffer/EOTfreeMetadata completed");
  EOTfreeMetadata(&meta);

  /* --- fixture B: non-empty UTF-16 family name "Test" --- */
  unsigned eotLenB = 0;
  uint8_t *eotB = buildEot(&eotLenB, 0, 8);
  CHECK(eotB != NULL, "fixture B construction");
  struct EOTMetadata metaB;
  rc = EOTfillMetadata(eotB, eotLenB, &metaB);
  CHECK(rc == EOT_SUCCESS, "header with family name parses");
  CHECK(metaB.familyNameSize == 8, "familyNameSize is 8 UTF-16 bytes");
  CHECK(metaB.familyName != NULL && metaB.familyName[0] == 'T' && metaB.familyName[3] == 't',
        "family name reads as UTF-16 'Test'");
  EOTfreeMetadata(&metaB);
  free(eotB);

  /* --- negative paths --- */
  struct EOTMetadata metaNeg;
  rc = EOTfillMetadata(eot, 10, &metaNeg);
  CHECK(rc == EOT_INSUFFICIENT_BYTES, "truncated input is rejected");
  eot[8] = 0xAB; /* corrupt the version magic */
  rc = EOTfillMetadata(eot, eotLen, &metaNeg);
  CHECK(rc == EOT_CORRUPT_FILE, "corrupt version magic is rejected");
  eot[8] = 0x00;
  EOTprintError(EOT_INSUFFICIENT_BYTES, stderr);
  CHECK(1, "EOTprintError ran");

  /* --- files for the packaged eot2ttf tool (run by conanfile.py) --- */
  CHECK(writeFile("fixture.eot", eot, eotLen), "wrote fixture.eot");
  CHECK(writeFile("expected.ttf", TTF_PAYLOAD, PAYLOAD_LEN), "wrote expected.ttf");
  free(eot);

  printf("libeot consumer test: all %d checks passed\n", g_checks);
  return 0;
}
