/*
 * test_iec16022.c — consumer-side verification of the packaged iec16022.
 *
 * Everything here goes through the *installed* package: the public headers
 * iec16022ecc200.h / reedsol.h / image.h and the installed libiec16022.  This
 * is not a smoke test — every assertion exercises real encoder behaviour,
 * including a byte-exact comparison against the reference artefact shipped by
 * the upstream test suite (test/testsuite-example.text, embedded in
 * fixture_upstream.h).
 *
 * The CLI's popt dependency is deliberately not linked: popt is used only by
 * the iec16022 front-end, not by libiec16022.
 */
#if !defined(_POSIX_C_SOURCE)
#define _POSIX_C_SOURCE 200809L   /* fileno() */
#endif

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include <iec16022ecc200.h>
#include <reedsol.h>
#include <image.h>

#include "fixture_upstream.h"

static int checks;
static int failed;

static void check(int cond, const char *what)
{
	checks++;
	if (!cond) {
		failed++;
		printf("  FAIL: %s\n", what);
	}
}

/* ------------------------------------------------------------------ */
/* 0. fixture self-check                                               */
/* ------------------------------------------------------------------ */
/* The reference rows are embedded as a string-literal array.  If an element
   ever loses its trailing comma, C concatenates adjacent literals and leaves
   the remaining slots NULL — indexing them then segfaults instead of failing
   an assertion.  Validate the table up front so that becomes a readable
   FAIL rather than Signal 11. */
static int fixture_is_wellformed(void)
{
	int y;

	for (y = 0; y < FIXTURE_H; y++) {
		if (fixture_text[y] == NULL) {
			printf("  FAIL: fixture_text[%d] is NULL "
			       "(missing comma between string literals?)\n", y);
			failed++;
			checks++;
			return 0;
		}
		if (strlen(fixture_text[y]) < FIXTURE_W) {
			printf("  FAIL: fixture_text[%d] is shorter than %d\n",
			       y, FIXTURE_W);
			failed++;
			checks++;
			return 0;
		}
	}
	check(1, "embedded reference table is well formed (32 non-NULL rows)");
	return 1;
}

/* ------------------------------------------------------------------ */
/* 1. encoder: auto-selected symbol must match the upstream reference   */
/* ------------------------------------------------------------------ */
static void test_encoder_matches_upstream_fixture(void)
{
	int W = 0, H = 0, len = 0, maxlen = 0, ecclen = 0;
	char *encoding = NULL;
	unsigned char *grid;

	grid = iec16022ecc200(&W, &H, &encoding, (int)strlen(FIXTURE_BARCODE),
			      (const unsigned char *)FIXTURE_BARCODE,
			      &len, &maxlen, &ecclen);
	check(grid != NULL, "iec16022ecc200() returned a grid");
	if (!grid) {
		free(encoding);
		return;
	}

	check(W == FIXTURE_W, "auto-selected width matches upstream (32)");
	check(H == FIXTURE_H, "auto-selected height matches upstream (32)");
	/* 32x32 is 62 data / 36 ECC codewords; capacity and ECC come straight
	   from the symbol table, not from the payload. */
	check(maxlen == 62, "32x32 data capacity is 62 codewords");
	check(ecclen == 36, "32x32 symbol carries 36 ECC codewords");
	check(len > 0 && len <= maxlen,
	      "packed length is within the symbol capacity");
	check(encoding != NULL && *encoding != '\0',
	      "an encoding template was selected");

	if (W == FIXTURE_W && H == FIXTURE_H) {
		int y, mismatches = 0;
		for (y = 0; y < H; y++) {
			const char *ref = fixture_text[FIXTURE_H - 1 - y];
			int x;
			for (x = 0; x < W; x++) {
				int want = (ref[x] == '*') ? 1 : 0;
				if ((grid[y * W + x] ? 1 : 0) != want)
					mismatches++;
			}
		}
		check(mismatches == 0,
		      "all 1024 modules match test/testsuite-example.text");
	}

	/* ECC200 structure: a solid L finder along the left column and the
	   y==0 row, and alternating timing tracks on the opposite two edges. */
	{
		int x, y, l_ok = 1, timing_ok = 1;
		for (y = 0; y < H; y++)
			if (!grid[y * W])
				l_ok = 0;
		for (x = 0; x < W; x++)
			if (!grid[x])
				l_ok = 0;
		for (x = 0; x < W; x++)
			if (!!grid[(H - 1) * W + x] != ((x % 2) == 0))
				timing_ok = 0;
		for (y = 0; y < H; y++)
			if (!!grid[y * W + (W - 1)] != ((y % 2) == 0))
				timing_ok = 0;
		check(l_ok, "solid ECC200 L finder (left column + y==0 row)");
		check(timing_ok, "alternating timing tracks on the far edges");
	}

	free(grid);
	free(encoding);
}

/* ------------------------------------------------------------------ */
/* 2. explicitly requested sizes, and refusal of invalid ones          */
/* ------------------------------------------------------------------ */
static void test_explicit_size(void)
{
	static const struct { int w, h; } sizes[] = {
		{10, 10}, {16, 16}, {32, 32}, {64, 64}
	};
	size_t i;

	for (i = 0; i < sizeof(sizes) / sizeof(sizes[0]); i++) {
		int W = sizes[i].w, H = sizes[i].h, len = 0, maxlen = 0;
		unsigned char *grid;
		char msg[80];

		grid = iec16022ecc200(&W, &H, NULL, 2,
				      (const unsigned char *)"AB",
				      &len, &maxlen, NULL);
		sprintf(msg, "encoding fits the requested size %dx%d",
			sizes[i].w, sizes[i].h);
		check(grid != NULL, msg);
		if (grid) {
			check(W == sizes[i].w && H == sizes[i].h,
			      "requested size is honoured");
			check(maxlen == (int)(sizes[i].w == 10 ? 3 :
					      sizes[i].w == 16 ? 12 :
					      sizes[i].w == 32 ? 62 : 280),
			      "requested size reports its data capacity");
			free(grid);
		}
	}

	/* 13x13 is not an ECC200 symbol size: must be refused, not coerced. */
	{
		int W = 13, H = 13;
		unsigned char *grid = iec16022ecc200(&W, &H, NULL, 2,
						     (const unsigned char *)"AB",
						     NULL, NULL, NULL);
		check(grid == NULL, "invalid size 13x13 is rejected");
		free(grid);
	}
}

/* ------------------------------------------------------------------ */
/* 3. symbol capacity limit                                            */
/* ------------------------------------------------------------------ */
static void test_oversized_payload_rejected(void)
{
	char *payload = malloc(MAXBARCODE + 64);
	int W = 0, H = 0;
	unsigned char *grid;

	check(payload != NULL, "allocated oversized payload");
	if (!payload)
		return;
	memset(payload, 'A', MAXBARCODE + 63);   /* no digit-pair packing */
	payload[MAXBARCODE + 63] = '\0';

	grid = iec16022ecc200(&W, &H, NULL, (int)strlen(payload),
			      (const unsigned char *)payload, NULL, NULL, NULL);
	check(grid == NULL, "payload beyond MAXBARCODE is refused");
	free(grid);
	free(payload);
}

/* ------------------------------------------------------------------ */
/* 4. ECC200 Reed-Solomon: ISO/IEC 16022 Annex R reference vector      */
/* ------------------------------------------------------------------ */
static void test_reedsol_annex_r(void)
{
	/* ISO/IEC 16022 Annex R: 142 164 186 -> 114 25 5 88 102 (the upstream
	   helper prints out[4..0]). */
	static const unsigned char data[3] = {142, 164, 186};
	static const unsigned char expected[5] = {102, 88, 5, 25, 114};
	unsigned char out[5];
	int i, ok = 1;

	rs_init_gf(0x12d);
	rs_init_code(5, 1);
	rs_encode(3, data, out);

	for (i = 0; i < 5; i++)
		if (out[i] != expected[i])
			ok = 0;
	check(ok, "Reed-Solomon matches the ISO/IEC 16022 Annex R vector");
}

/* ------------------------------------------------------------------ */
/* 5. exported flag constant + GS1 encodation path                     */
/* ------------------------------------------------------------------ */
static void test_gs1_flag(void)
{
	int Wa = 0, Ha = 0, Wb = 0, Hb = 0, i, differs = 0;
	unsigned char *plain, *gs1;

	check(IEC16022_FLAG_GS1 == 1, "IEC16022_FLAG_GS1 public constant is 1");

	plain = iec16022ecc200f(&Wa, &Ha, NULL, 4,
				(const unsigned char *)"1234", NULL, NULL, NULL, 0);
	gs1 = iec16022ecc200f(&Wb, &Hb, NULL, 4,
			      (const unsigned char *)"1234", NULL, NULL, NULL,
			      IEC16022_FLAG_GS1);
	check(plain != NULL, "baseline (non-GS1) encode succeeded");
	check(gs1 != NULL, "GS1 encode succeeded");
	if (plain && gs1 && Wa == Wb && Ha == Hb) {
		for (i = 0; i < Wa * Ha; i++)
			if (plain[i] != gs1[i])
				differs = 1;
		check(differs, "GS1 mode changes the produced symbol");
	}
	free(plain);
	free(gs1);
}

/* ------------------------------------------------------------------ */
/* 6. image renderer: PNG signature, dimensions, 1 bpp bit depth       */
/* ------------------------------------------------------------------ */
static void test_image_write_png(void)
{
	const char *path = "test_iec16022_image.png";
	static const unsigned char png_magic[8] =
		{0x89, 'P', 'N', 'G', '\r', '\n', 0x1a, '\n'};
	unsigned char buf[64];
	Image *img;
	FILE *f;
	size_t got;

	img = ImageNew(FIXTURE_W + 2, FIXTURE_H + 2, 2);
	check(img != NULL, "ImageNew() allocated the fixture-sized bitmap");
	if (!img)
		return;
	img->Colour[0] = 0xFFFFFF;	/* index 0 = white background */
	img->Colour[1] = 0;		/* index 1 = black module     */
	{
		int x, y;
		for (y = 0; y < FIXTURE_H; y++)
			for (x = 0; x < FIXTURE_W; x++)
				if (fixture_text[FIXTURE_H - 1 - y][x] == '*')
					ImagePixel(img, x + 1, y) = 1;
	}

	f = fopen(path, "wb");
	check(f != NULL, "opened PNG output file");
	if (!f) {
		ImageFree(img);
		return;
	}
	ImageWritePNG(img, fileno(f), -1, -1, "iec16022 test");
	fclose(f);
	ImageFree(img);

	f = fopen(path, "rb");
	check(f != NULL, "reopened the written PNG");
	if (!f) {
		remove(path);
		return;
	}
	got = fread(buf, 1, sizeof(buf), f);
	fclose(f);
	remove(path);

	check(got > 33, "PNG holds at least a signature and an IHDR chunk");
	if (got > 33) {
		check(memcmp(buf, png_magic, 8) == 0, "valid PNG signature");
		check(buf[12] == 'I' && buf[13] == 'H' && buf[14] == 'D' &&
		      buf[15] == 'R', "first chunk is IHDR");
		/* IHDR width/height are big-endian 32-bit values. */
		check(buf[16] == 0 && buf[19] == (unsigned char)(FIXTURE_W + 2),
		      "IHDR width is W+2");
		check(buf[20] == 0 && buf[23] == (unsigned char)(FIXTURE_H + 2),
		      "IHDR height is H+2");
		check(buf[24] == 1, "IHDR bit depth is 1 (monochrome)");
	}
}

int main(void)
{
	printf("test iec16022 0.3.1: consumer-side verification\n");

	if (!fixture_is_wellformed()) {
		printf("test iec16022 0.3.1: %d checks, %d failed\n", checks,
		       failed);
		printf("RESULT: FAIL\n");
		return 1;
	}

	test_encoder_matches_upstream_fixture();
	test_explicit_size();
	test_oversized_payload_rejected();
	test_reedsol_annex_r();
	test_gs1_flag();
	test_image_write_png();

	printf("test iec16022 0.3.1: %d checks, %d failed\n", checks, failed);
	if (failed) {
		printf("RESULT: FAIL\n");
		return 1;
	}
	printf("RESULT: PASS\n");
	return 0;
}
