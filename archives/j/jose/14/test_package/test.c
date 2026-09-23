/*
 * test_package consumer test for jose/14 — public API only (HarmonyOS PC, aarch64).
 *
 * Exercises the installed <jose/b64.h> URL-safe Base64 codec against the
 * semantics that v14's lib/b64.c actually implements: unpadded output, the
 * '-'/'_' alphabet only, size probes with o == NULL, and SIZE_MAX for inputs
 * whose length or characters are not representable. Every expectation here is
 * derived from the shipped source, not from guesswork.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include <jose/b64.h>

#define SZ(type) ((size_t) -1)

static int g_total;
static int g_pass;

#define CHECK(cond, name)                                                  \
	do {                                                               \
		g_total++;                                                 \
		if (cond) {                                                \
			g_pass++;                                          \
			printf("[PASS] %s\n", name);                       \
		} else {                                                   \
			printf("[FAIL] %s\n", name);                       \
		}                                                          \
	} while (0)

/* All output characters must come from the URL-safe map. */
static int only_urlsafe(const char *s, size_t n)
{
	size_t i;

	for (i = 0; i < n; i++) {
		if (strchr(JOSE_B64_MAP, s[i]) == NULL)
			return 0;
	}
	return 1;
}

static int all_bytes_roundtrip(void)
{
	uint8_t raw[256];
	char enc[512];
	uint8_t dec[512];
	size_t elen, dlen, i;

	for (i = 0; i < sizeof(raw); i++)
		raw[i] = (uint8_t) i;

	elen = jose_b64_enc_buf(raw, sizeof(raw), enc, sizeof(enc));
	if (elen != 342) { /* 256 % 3 == 1 -> 85*4 + 2, no padding */
		printf("  encoded length = %zu (want 342)\n", elen);
		return 0;
	}
	if (!only_urlsafe(enc, elen))
		return 0;

	dlen = jose_b64_dec_buf(enc, elen, dec, sizeof(dec));
	if (dlen != sizeof(raw)) {
		printf("  decoded length = %zu (want 256)\n", dlen);
		return 0;
	}
	return memcmp(dec, raw, sizeof(raw)) == 0;
}

int main(void)
{
	const char plain[] = "hello jose";
	const size_t plain_len = sizeof(plain) - 1;
	char enc[64];
	char dec[64];
	size_t n;

	printf("== jose/%s public b64 API (consumer view) ==\n", "14");

	/* 1 - the map is the 64-symbol URL-safe alphabet. */
	CHECK(strlen(JOSE_B64_MAP) == 64, "JOSE_B64_MAP has 64 symbols");

	/* 2 - a NULL output buffer is a size probe, not a write. */
	n = jose_b64_enc_buf(plain, plain_len, NULL, 0);
	CHECK(n == 14, "encode size probe returns 14 for 10 bytes");

	/* 3 - encoding returns the same length the probe promised. */
	memset(enc, 0, sizeof(enc));
	n = jose_b64_enc_buf(plain, plain_len, enc, sizeof(enc));
	CHECK(n == 14, "encode writes 14 characters");

	/* 4 - and the value is the URL-safe, unpadded form. */
	CHECK(n == 14 && strcmp(enc, "aGVsbG8gam9zZQ") == 0,
	      "encode matches known vector aGVsbG8gam9zZQ");

	/* 5 - no padding, no '+' or '/' anywhere in the output. */
	CHECK(n == 14 && only_urlsafe(enc, n), "encode output is URL-safe only");

	/* 6 - decode probe reports the plaintext length. */
	n = jose_b64_dec_buf("aGVsbG8gam9zZQ", 14, NULL, 0);
	CHECK(n == 10, "decode size probe returns 10");

	/* 7 - decode round trip reproduces the input bytes. */
	memset(dec, 0, sizeof(dec));
	jose_b64_enc_buf(plain, plain_len, enc, sizeof(enc));
	n = jose_b64_dec_buf(enc, 14, dec, sizeof(dec));
	CHECK(n == plain_len && memcmp(dec, plain, plain_len) == 0,
	      "decode round trip equals original");

	/* 8 - an output buffer that is too small is rejected, not overflowed. */
	n = jose_b64_dec_buf(enc, 14, dec, 5);
	CHECK(n == SZ(size_t), "decode with undersized buffer returns SIZE_MAX");

	/* 9 - a 1-character group cannot exist in base64. */
	n = jose_b64_dec_buf("a", 1, NULL, 0);
	CHECK(n == SZ(size_t), "decode probe of 1 char returns SIZE_MAX");

	/* 10 - the standard alphabet's '+' is not accepted. */
	memset(dec, 0, sizeof(dec));
	n = jose_b64_dec_buf("ab+", 3, dec, sizeof(dec));
	CHECK(n == SZ(size_t), "decode rejects '+' (standard alphabet)");

	/* 11 - every byte value survives a full round trip. */
	CHECK(all_bytes_roundtrip(), "all 256 byte values round trip");

	printf("TOTAL=%d PASS=%d FAIL=%d\n", g_total, g_pass, g_total - g_pass);
	if (g_pass != g_total)
		return 1;
	printf("ALL TESTS PASSED\n");
	return 0;
}
