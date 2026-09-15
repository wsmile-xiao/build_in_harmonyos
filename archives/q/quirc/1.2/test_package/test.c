/* test_package/test.c — quirc 1.2 consumer test (Conan L1).
 *
 * Acts as a library consumer: feeds a known, fixed QR code (version 1,
 * ECC level L, mask 0, byte payload "quirc-1.2-ohos") as a grayscale
 * raster into the public quirc API and asserts the decoded result.
 * Exit code 0 = all assertions passed; 1 = failure.
 *
 * The embedded matrix is a valid QR symbol verified against this same
 * upstream decoder on the OHOS device (qrtest 3/3 decoded); it only
 * exercises documented public API behavior, no upstream files modified.
 */
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include <quirc.h>

/* 21x21 module matrix, 1 = dark module */
static const unsigned char QR_MATRIX[21][21] = {
    {1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 1, 0, 1, 0, 1, 1, 1, 1, 1, 1, 1},
    {1, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 1, 0, 1, 0, 0, 0, 0, 0, 1},
    {1, 0, 1, 1, 1, 0, 1, 0, 1, 0, 1, 0, 0, 0, 1, 0, 1, 1, 1, 0, 1},
    {1, 0, 1, 1, 1, 0, 1, 0, 0, 0, 0, 0, 1, 0, 1, 0, 1, 1, 1, 0, 1},
    {1, 0, 1, 1, 1, 0, 1, 0, 0, 1, 0, 0, 1, 0, 1, 0, 1, 1, 1, 0, 1},
    {1, 0, 0, 0, 0, 0, 1, 0, 0, 1, 1, 1, 0, 0, 1, 0, 0, 0, 0, 0, 1},
    {1, 1, 1, 1, 1, 1, 1, 0, 1, 0, 1, 0, 1, 0, 1, 1, 1, 1, 1, 1, 1},
    {0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 1, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0},
    {1, 1, 1, 0, 1, 1, 1, 1, 1, 0, 1, 0, 1, 1, 1, 0, 0, 0, 1, 0, 0},
    {1, 1, 0, 1, 1, 0, 0, 1, 1, 0, 1, 0, 1, 0, 1, 1, 1, 0, 0, 0, 1},
    {0, 0, 1, 1, 0, 0, 1, 1, 1, 1, 0, 1, 1, 0, 0, 0, 1, 1, 1, 1, 1},
    {0, 1, 0, 0, 0, 0, 0, 1, 1, 0, 1, 0, 1, 1, 0, 0, 0, 0, 0, 0, 0},
    {0, 1, 0, 1, 0, 0, 1, 1, 1, 1, 0, 1, 0, 1, 0, 0, 1, 0, 0, 0, 1},
    {0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 1, 1, 1, 1, 0, 0, 1, 1, 1, 0, 1},
    {1, 1, 1, 1, 1, 1, 1, 0, 1, 1, 1, 1, 1, 0, 0, 0, 1, 1, 1, 1, 1},
    {1, 0, 0, 0, 0, 0, 1, 0, 1, 0, 1, 1, 0, 1, 0, 0, 0, 0, 0, 1, 1},
    {1, 0, 1, 1, 1, 0, 1, 0, 1, 1, 0, 0, 0, 0, 0, 1, 0, 1, 0, 1, 0},
    {1, 0, 1, 1, 1, 0, 1, 0, 0, 1, 0, 1, 1, 0, 1, 1, 1, 1, 0, 1, 0},
    {1, 0, 1, 1, 1, 0, 1, 0, 1, 1, 0, 1, 1, 1, 1, 0, 1, 0, 0, 0, 1},
    {1, 0, 0, 0, 0, 0, 1, 0, 1, 1, 0, 0, 1, 0, 0, 0, 1, 0, 0, 1, 0},
    {1, 1, 1, 1, 1, 1, 1, 0, 1, 1, 1, 1, 0, 0, 0, 0, 1, 0, 0, 1, 1},
};

#define SCALE 4  /* pixels per module */
#define QUIET 4  /* quiet-zone modules on each side */
#define W ((21 + 2 * QUIET) * SCALE)
#define H W

static int failures = 0;

#define CHECK(cond, msg)                                                  \
	do {                                                              \
		if (!(cond)) {                                            \
			printf("FAIL: %s (at %s:%d)\n", msg, __FILE__,    \
			       __LINE__);                                 \
			failures++;                                       \
		} else {                                                  \
			printf("ok: %s\n", msg);                          \
		}                                                         \
	} while (0)

static void render(const unsigned char matrix[21][21], unsigned char *img)
{
	int x, y, dx, dy;
	memset(img, 255, (size_t)W * H);
	for (y = 0; y < 21; y++)
		for (x = 0; x < 21; x++)
			if (matrix[y][x])
				for (dy = 0; dy < SCALE; dy++)
					for (dx = 0; dx < SCALE; dx++) {
						int px = (x + QUIET) *
								SCALE + dx;
						int py = (y + QUIET) *
								SCALE + dy;
						img[py * W + px] = 0;
					}
}

int main(void)
{
	struct quirc *q;
	int w, h, num_codes, i;
	uint8_t *pix;
	static unsigned char img[W * H];

	/* API surface: strerror must return a message for every code */
	CHECK(quirc_strerror(QUIRC_SUCCESS) != NULL, "quirc_strerror");

	q = quirc_new();
	CHECK(q != NULL, "quirc_new");
	if (!q)
		return 1;

	CHECK(quirc_resize(q, W, H) == 0, "quirc_resize");

	pix = quirc_begin(q, &w, &h);
	CHECK(pix != NULL, "quirc_begin returns buffer");
	CHECK(w == W && h == H, "quirc_begin reports feed size");

	render(QR_MATRIX, img);
	memcpy(pix, img, (size_t)W * H);
	quirc_end(q);

	num_codes = quirc_count(q);
	CHECK(num_codes == 1, "quirc_count == 1");

	for (i = 0; i < num_codes; i++) {
		struct quirc_code code;
		struct quirc_data data;
		quirc_decode_error_t err;

		quirc_extract(q, i, &code);
		CHECK(code.size == 21, "grid size == 21 (version 1)");

		memset(&data, 0, sizeof(data));
		err = quirc_decode(&code, &data);
		CHECK(err == QUIRC_SUCCESS, "quirc_decode succeeds");
		CHECK(data.payload_len == 14, "payload length == 14");
		CHECK(memcmp(data.payload, "quirc-1.2-ohos", 14) == 0,
		      "payload content matches");
		CHECK(data.version == 1, "version == 1");
		CHECK(data.ecc_level == QUIRC_ECC_LEVEL_L, "ecc level == L");
		CHECK(data.mask == 0, "mask == 0");
		CHECK(data.data_type == QUIRC_DATA_TYPE_BYTE,
		      "data type == BYTE");
	}

	/* Behavior: a fresh decoder on a blank (all-white) image finds
	 * no QR codes. (A quirc instance accumulates detected codes
	 * across quirc_end() calls, so a new instance is required.) */
	{
		struct quirc *q2 = quirc_new();
		CHECK(q2 != NULL, "quirc_new (second instance)");
		if (q2) {
			CHECK(quirc_resize(q2, W, H) == 0,
			      "quirc_resize (second instance)");
			pix = quirc_begin(q2, &w, &h);
			CHECK(pix != NULL, "quirc_begin (second instance)");
			memset(pix, 255, (size_t)W * H);
			quirc_end(q2);
			CHECK(quirc_count(q2) == 0,
			      "blank image yields 0 codes");
			quirc_destroy(q2);
		}
	}

	quirc_destroy(q);

	if (failures) {
		printf("consumer test: %d check(s) FAILED\n", failures);
		return 1;
	}
	printf("consumer test: all checks passed\n");
	return 0;
}
